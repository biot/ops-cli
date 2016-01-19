#
# Copyright (C) 2016 Bert Vermeulen <bert@biot.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from collections import OrderedDict

import opscli.ovsdb as ovsdb


# TODO should be a global facility
DEFAULTS = {
    'LLDP_HOLDTIME': 4,
    'LLDP_TIMER': 30,
    'LLDP_TLV_MGMT_ADDR': 'true',
    'LLDP_TLV_PROTO_VLAN_ID': 'true',
    'LLDP_TLV_PORT_PROTO_ID': 'true',
    'LLDP_TLV_PORT_VLAN_NAME': 'true',
    'LLDP_TLV_PORT_DESC': 'true',
    'LLDP_TLV_PORT_VLAN_ID': 'true',
    'LLDP_TLV_SYS_CAP': 'true',
    'LLDP_TLV_SYS_DESC': 'true',
    'LLDP_TLV_SYS_NAME': 'true',
}


lldp_tlv_keys = (
    (
        'lldp_tlv_mgmt_addr_enable',
        'LLDP_TLV_MGMT_ADDR',
        'management-address',
        'Management address',
    ),
    (
        'lldp_tlv_port_proto_vlan_id_enable',
        'LLDP_TLV_PROTO_VLAN_ID',
        'port-protocol-vlan-id',
        'Port protocol VLAN ID',
    ),
    (
        'lldp_tlv_port_proto_id_enable',
        'LLDP_TLV_PORT_PROTO_ID',
        'port-protocol-id',
        'Port protocol ID',
    ),
    (
        'lldp_tlv_port_vlan_name_enable',
        'LLDP_TLV_PORT_VLAN_NAME',
        'port-vlan-name',
        'Port VLAN name',
    ),
    (
        'lldp_tlv_port_desc_enable',
        'LLDP_TLV_PORT_DESC',
        'port-description',
        'Port description',
    ),
    (
        'lldp_tlv_port_vlan_id_enable',
        'LLDP_TLV_PORT_VLAN_ID',
        'port-vlan-id',
        'Port VLAN ID',
    ),
    (
        'lldp_tlv_sys_cap_enable',
        'LLDP_TLV_SYS_CAP',
        'system-capabilities',
        'System capabilities',
    ),
    (
        'lldp_tlv_sys_desc_enable',
        'LLDP_TLV_SYS_DESC',
        'system-description',
        'System description',
    ),
    (
        'lldp_tlv_sys_name_enable',
        'LLDP_TLV_SYS_NAME',
        'system-name',
        'System name',
    ),
)


def get_global_config():
    data = {}
    results = ovsdb.get_map('System', column='other_config')
    data['lldp_enable'] = results.get('lldp_enable', False) == 'true'
    data['lldp_holdtime'] = int(results.get('lldp_hold',
                                            DEFAULTS['LLDP_HOLDTIME']))
    data['lldp_tx_interval'] = int(results.get('lldp_tx_interval',
                                               DEFAULTS['LLDP_TIMER']))
    data['lldp_mgmt_addr'] = results.get('lldp_mgmt_addr', '')

    return data


def get_tlv_keys(enabled=None, key='config'):
    if key not in ('config', 'cli', 'descr'):
        raise Exception('invalid key')
    data = OrderedDict()
    results = ovsdb.get_map('System', column='other_config')
    for config_key, default, cli_word, descr in lldp_tlv_keys:
        value = results.get(config_key, DEFAULTS[default]) == 'true'
        if enabled is None or enabled == value:
            if key == 'config':
                od_key = config_key
            elif key == 'cli':
                od_key = cli_word
            else:
                od_key = descr
            data[od_key] = value

    return data


def get_intf_config(intf=None):
    results = OrderedDict()
    if intf:
        conditions = [['name', '==', str(intf)]]
    else:
        conditions = []
    rows = ovsdb.get('Interface', columns=['name', 'other_config'],
                     conditions=conditions)
    for row in rows:
        # TODO should get 'rxtx' from defaults
        state = 'rxtx'
        for key, value in row['other_config'][1]:
            if key == 'lldp_enable_dir':
                state = value
                break
        if state == 'off':
            rx = tx = False
        else:
            rx = tx = True
            if state.find('rx') == -1:
                rx = False
            if state.find('tx') == -1:
                tx = False
        results[row['name']] = (rx, tx)

    return results


# TODO nothing in there, no idea if this is right
def get_intf_stats(intf=None):
    results = {}
    totals = {
        'lldp_insert': 0,
        'lldp_delete': 0,
        'lldp_drop': 0,
        'lldp_ageout': 0,
    }

    if intf:
        conditions = [['name', '==', str(intf)]]
    else:
        conditions = []
    rows = ovsdb.get('Interface', columns=['name', 'lldp_statistics'],
                     conditions=conditions)
    for row in rows:
        intf_name = row['name']
        for key, value in row['lldp_statistics'][1]:
            results[intf_name][key] = value
            if key in totals:
                totals[key] += value

    return results, totals
