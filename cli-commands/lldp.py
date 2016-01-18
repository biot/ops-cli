#
# Copyright (C) 2015 Bert Vermeulen <bert@biot.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from opscli.command import *
from opscli.options import *
from opscli.tokens import *
from opscli.flags import *
from opscli.context import *
from opscli.output import *
import ops.lldp
import opscli.ovsdb as ovsdb


tlv_keys = (
    ('management-address', 'lldp_tlv_mgmt_addr_enable', 'Management address'),
    ('port-description', 'lldp_tlv_port_desc_enable', 'Port description'),
    ('port-protocol-id', 'lldp_tlv_port_proto_id_enable', 'Port protocol ID'),
    ('port-protocol-vlan-id', 'lldp_tlv_port_proto_vlan_id_enable',
        'Port protocol VLAN ID'),
    ('port-vlan-id', 'lldp_tlv_port_vlan_id_enable', 'Port VLAN ID'),
    ('port-vlan-name', 'lldp_tlv_port_vlan_name_enable', 'Port VLAN name'),
    ('system-capabilities', 'lldp_tlv_sys_cap_enable', 'System capabilities'),
    ('system-description', 'lldp_tlv_sys_desc_enable', 'System description'),
    ('system-name', 'lldp_tlv_sys_name_enable', 'System name'),
)


class Conf_lldp(Command):
    '''Configure LLDP parameters'''
    command = 'lldp'
    flags = (F_NO,)
    options = (
        Opt_one(('enable', 'Enable or disable LLDP')),
        Opt_all_order(
            ('management-address', 'LLDP management IP address'),
            TIPAddress(help_text='LLDP management IP address'),
        ),
        Opt_all_order(
            ('holdtime', 'Hold time multiplier'),
            TInteger(min_int=2, max_int=10, help_text='Hold time multiplier'),
        ),
        Opt_all_order(
            ('timer', 'LLDP status transmit interval'),
            TInteger(min_int=5, max_int=32768,
                     help_text='Interval in seconds'),
        ),
        Opt_all_order(
            ('select-tlv', 'Specify TLVs to send and receive in LLDP packets'),
            TString(
                ('management-address', 'Select management-address TLV'),
                ('port-description', 'Select management-address TLV'),
                ('port-protocol-id', 'Select port-description TLV'),
                ('port-protocol-vlan-id', 'Select port-protocol-id TLV'),
                ('port-vlan-id', 'Select port-vlan-id TLV'),
                ('port-vlan-name', 'Select port-vlan-name TLV'),
                ('system-capabilities', 'Select system-capabilities TLV'),
                ('system-description', 'Select system-description TLV'),
                ('system-name', 'Select system-name TLV'),
            ),
        ),
        Opt_all_order(
            ('clear', 'Clear LLDP information'),
            TString(
                ('counters', 'Clear LLDP counters'),
                ('neighbors', 'Clear LLDP neighbor entries'),
            ),
        ),
    )

    def run(self, opts, flags):
        while opts:
            if opts[0] == 'enable':
                value = F_NO not in flags
                ovsdb.map_set_key('System', 'other_config', 'lldp_enable',
                                  str(value).lower())
                opts.pop(0)

            elif opts[0] == 'management-address':
                if F_NO in flags:
                    ovsdb.map_delete_key('System', 'other_config',
                                         'lldp_mgmt_addr')
                else:
                    ovsdb.map_set_key('System', 'other_config',
                                      'lldp_mgmt_addr', str(opts[1]))
                opts.pop(0)
                opts.pop(0)

            elif opts[0] == 'holdtime':
                if F_NO in flags:
                    ovsdb.map_delete_key('System', 'other_config', 'lldp_hold')
                else:
                    ovsdb.map_set_key('System', 'other_config', 'lldp_hold',
                                      str(opts[1]))
                opts.pop(0)
                opts.pop(0)

            elif opts[0] == 'timer':
                if F_NO in flags:
                    ovsdb.map_delete_key('System', 'other_config',
                                         'lldp_tx_interval')
                else:
                    ovsdb.map_set_key('System', 'other_config',
                                      'lldp_tx_interval', str(opts[1]))
                opts.pop(0)
                opts.pop(0)

            elif opts[0] == 'select-tlv':
                for word, map_key, descr in tlv_keys:
                    if opts[1] == word:
                        key = map_key
                        break
                value = str(F_NO not in flags).lower()
                ovsdb.map_set_key('System', 'other_config', key, value)
                opts.pop(0)
                opts.pop(0)

            elif opts[0] == 'clear':
                if opts[1] == 'counters':
                    sem = 'lldp_num_clear_counters_requested'
                elif opts[1] == 'neighbors':
                    sem = 'lldp_num_clear_table_requested'
                req = ovsdb.get_map('System', 'status')
                counter = int(req.get(sem, 0))
                counter += 1
                ovsdb.map_set_key('System', 'status', sem, str(counter))
                opts.pop(0)
                opts.pop(0)

register_commands((Conf_lldp,), tree='config')


class Interface_lldp(Command):
    '''Configure LLDP parameters'''
    command = 'lldp'
    flags = (F_NO,)
    options = (
        Opt_any(
            ('reception', 'Set LLDP reception'),
            ('transmission', 'Set LLDP transmission'),
            required=True,
        ),
    )

    def run(self, opts, flags):
        intf_token = context_get().obj
        condition = ['name', '==', str(intf_token)]
        intf_other_map = ovsdb.get_map('Interface', 'other_config',
                                       conditions=[condition])
        # TODO should get 'rxtx' from defaults
        old_state = intf_other_map.get('lldp_enable_dir', 'rxtx')
        rx = tx = True
        if old_state == 'off':
            rx = tx = False
        else:
            if old_state.find('rx') == -1:
                rx = False
            if old_state.find('tx') == -1:
                tx = False

        while opts:
            if opts[0] == 'reception':
                rx = F_NO not in flags
                opts.pop(0)
            elif opts[0] == 'transmission':
                tx = F_NO not in flags
                opts.pop(0)

        if not rx and not tx:
            new_state = 'off'
        else:
            new_state = ''
            if rx:
                new_state += 'rx'
            if tx:
                new_state += 'tx'
        if old_state != new_state:
            ovsdb.map_set_key('Interface', 'other_config', 'lldp_enable_dir',
                              new_state, conditions=[condition])


register_commands((Interface_lldp,), tree='interface')


def bool_yes_no(value):
    if value:
        return 'Yes'
    else:
        return 'No'


def show_config(intf):
    cli_out("LLDP global configuration:")
    data = ops.lldp.get_global_config()
    out_kv('lldp', data)
    cli_out()

    show_tlv()
    cli_out()

    cli_out("Port configuration:")
    intf_data = ops.lldp.get_intf_config(intf)
    data = []
    for interface in intf_data:
        rx = bool_yes_no(intf_data[interface][0])
        tx = bool_yes_no(intf_data[interface][1])
        data.append([interface, rx, tx])
    out_table(data, title=['Interface', 'Receive', 'Transmit'], indent=2)


def show_neighbors(intf):
    # TODO
    cli_out("nei")
    cli_out("interface %s" % intf)


def show_stats(intf):
    intf_data, totals = ops.lldp.get_intf_stats(intf)
    # TODO
    print totals
    print intf_data


def show_tlv():
    results = ovsdb.get_map('System', 'other_config')
    cli_out('TLVs advertised:')
    data = ops.lldp.get_tlv_keys(enabled=True, key='config')
    out_keys('lldp_tlv', data)


class Show_lldp(Command):
    '''LLDP settings and statistics'''
    command = 'show lldp'
    options = (
        Opt_any_order(
            TString(
                ('configuration', 'LLDP configuration'),
                ('neighbor-info', 'LLDP neighbor information'),
                ('statistics', 'LLDP statistics'),
            ),
            TInterface(),
        ),
        Opt_one(
            ('tlv', 'TLVs advertised by LLDP'),
        ),
    )

    def run(self, opts, flags):
        if not opts:
            raise Exception(CLI_ERR_INCOMPLETE)

        while opts:
            if opts[0] == 'tlv':
                show_tlv()
                opts.pop(0)
            else:
                # The other keywords can be followed by an optional interface.
                if len(opts) == 2:
                    intf = opts[1]
                    opts.pop(1)
                else:
                    intf = None

                if opts[0] == 'configuration':
                    show_config(intf)
                elif opts[0] == 'neighbor-info':
                    show_neighbors(intf)
                elif opts[0] == 'statistics':
                    show_stats(intf)
                opts.pop(0)


register_commands((Show_lldp,))
