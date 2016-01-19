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

# TODO
import opscli.ovsdb as ovsdb

# TODO
from ops.lldp import DEFAULTS


def generate_cli():
    lines = []
    results = ovsdb.get_map('System', column='other_config')
    if results.get('lldp_enable', '') == 'true':
        lines.append('lldp enable')

    val = results.get('lldp_hold')
    if val and val != DEFAULTS['LLDP_HOLDTIME']:
        lines.append("lldp holdtime %s" % val)

    val = results.get('lldp_tx_interval')
    if val and val != DEFAULTS['LLDP_TIMER']:
        lines.append("lldp timer %s" % val)

    val = results.get('lldp_mgmt_addr')
    if val:
        lines.append("lldp management-address %s" % val)

    lldp_tlv_config = (
        (
            'lldp_tlv_mgmt_addr_enable',
            'LLDP_TLV_MGMT_ADDR',
            'management-address'
        ),
        (
            'lldp_tlv_port_proto_vlan_id_enable',
            'LLDP_TLV_PROTO_VLAN_ID',
            'port-protocol-vlan-id'
        ),
        (
            'lldp_tlv_port_proto_id_enable',
            'LLDP_TLV_PORT_PROTO_ID',
            'port-protocol-id'
        ),
        (
            'lldp_tlv_port_vlan_name_enable',
            'LLDP_TLV_PORT_VLAN_NAME',
            'port-vlan-name'
        ),
        (
            'lldp_tlv_port_desc_enable',
            'LLDP_TLV_PORT_DESC',
            'port-description'
        ),
        (
            'lldp_tlv_port_vlan_id_enable',
            'LLDP_TLV_PORT_VLAN_ID',
            'port-vlan-id'
        ),
        (
            'lldp_tlv_sys_cap_enable',
            'LLDP_TLV_SYS_CAP',
            'system-capabilities'
        ),
        (
            'lldp_tlv_sys_desc_enable',
            'LLDP_TLV_SYS_DESC',
            'system-description'
        ),
        (
            'lldp_tlv_sys_name_enable',
            'LLDP_TLV_SYS_NAME',
            'system-name'
        ),
    )
    for key, default, word in lldp_tlv_config:
        val = results.get(key)
        if val and val != DEFAULTS[default]:
            lines.append("no lldp select-tlv %s" % word)

    return lines
