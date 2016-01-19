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

import sys
from collections import OrderedDict as OD

CLI_MSG_MOTD = 'OpenSwitch shell'
PROMPT_READ = '> '
PROMPT_WRITE = '# '

CLI_ERR_NOCOMMAND = '% No such command.'
CLI_ERR_INCOMPLETE = '% Incomplete command.'
CLI_ERR_BADOPTION_ARG = '%% Invalid option %s.'
CLI_ERR_BADOPTION = '% Invalid option.'
CLI_ERR_OPT_REQD = '% Required option missing.'
CLI_ERR_NOMATCH = '% There is no matched command.'
CLI_ERR_AMBIGUOUS = '% Ambiguous command.'
CLI_ERR_NOHELP_UNK = '% No help available: unknown command.'
CLI_ERR_SUPERFLUOUS = '% Superfluous option.'

_keymaps = {
    'system': OD([
        ('vendor', 'Vendor'),
        ('Product Name', 'Product name'),
        ('platform_name', 'Platform'),
        ('serial_number', 'Serial number'),
        ('asset_tag_number', 'Asset tag'),
        ('manufacturer', 'Manufacturer'),
        ('manufacture_date', 'Manufacture date'),
        ('part_number', 'Part number'),
        ('device_version', 'Device version'),
        ('onie_version', 'ONIE version'),
        ('interface_count', 'Interfaces'),
        ('number_of_macs', 'MAC addresses'),
        ('base_mac_address', 'Base MAC address'),
        ('max_interface_speed', 'Max interface speed'),
        ('max_transmission_unit', 'MTU'),
    ]),
    'system-fan': OD([
        ('fan_speed_override', 'Fan speed override'),
    ]),
    'interface': OD([
        ('admin_state', 'Administrative state'),
        ('link_state', 'Operational state'),
        ('duplex', 'Duplex'),
        ('link_speed', 'Speed'),
        ('link_resets', 'Resets'),
        ('mac_in_use', 'MAC address in use'),
    ]),
    'interface-transceiver': OD([
        ('connector', 'Connector'),
        ('mac_addr', 'Mac address'),
        ('max_speed', 'Max speed'),
        ('pluggable', 'Removable'),
        ('speeds', 'Supported speeds'),
    ]),
    'mgmt-interface': OD([
        ('link_state', 'Operational state'),
        ('ip', 'IPv4 address/len'),
        ('default_gateway', 'IPv4 default route'),
        ('ipv6_linklocal', 'IPv6 link local address/prefix'),
    ]),
    'lldp': OD([
        ('lldp_enable', 'Enabled'),
        ('lldp_holdtime', 'Hold time'),
        ('lldp_tx_interval', 'Transmit interval'),
        ('lldp_mgmt_addr', 'Management address'),
    ]),
    'lldp_tlv': OD([
        ('lldp_tlv_mgmt_addr_enable', 'Management address',),
        ('lldp_tlv_port_proto_vlan_id_enable', 'Port protocol VLAN ID',),
        ('lldp_tlv_port_proto_id_enable', 'Port protocol ID',),
        ('lldp_tlv_port_vlan_name_enable', 'Port VLAN name',),
        ('lldp_tlv_port_desc_enable', 'Port description',),
        ('lldp_tlv_port_vlan_id_enable', 'Port VLAN ID',),
        ('lldp_tlv_sys_cap_enable', 'System capabilities',),
        ('lldp_tlv_sys_desc_enable', 'System description',),
        ('lldp_tlv_sys_name_enable', 'System name',),
    ]),
}


def cli_out(msg=''):
    print msg


def cli_wrt(msg):
    '''cli_out() without added linefeed.'''
    sys.stdout.write(msg)
    sys.stdout.flush()


def cli_warn(msg):
    cli_out('warning: ' + msg)


def cli_err(msg):
    cli_out(msg)


def out_kv(keymap_name, data):
    '''
    Output key/value pairs, with keys substituted by the value from the
    given keymap.
    '''
    keymap = _keymaps[keymap_name]
    max_field_len = 0
    for key in data:
        if key in keymap:
            max_field_len = max(max_field_len, len(keymap[key]))
    for key in keymap:
        if key in data:
            if isinstance(data[key], bool):
                if data[key]:
                    value = 'Yes'
                else:
                    value = 'Yes'
            else:
                value = str(data[key])
            cli_out("  %-*s: %s" % (max_field_len, keymap[key], value))


def out_keys(keymap_name, data):
    keymap = _keymaps[keymap_name]
    for key in keymap:
        if key in data:
            cli_out("  %s" % keymap[key])


# TODO adjust width of left column to longest command
def cli_help(items, end='\n'):
    for item in items:
        cli_wrt("  %-20s %s%s" % (item, getattr(item, 'help_text', ''), end))


# TODO pretty columns
def fmt_cols(data):
    '''Arrange strings into columns depending on terminal width and the
    longest string.'''
    return '    '.join(data)


def out_table(data, title=None, indent=0):
    if not data:
        return
    if title:
        len_row = title
    else:
        len_row = data[0]
    maxlen = [0] * len(len_row)
    for f in range(len(len_row)):
        if len(len_row[f]) > maxlen[f]:
            maxlen[f] = len(len_row[f])
    fmt = ' ' * indent
    for l in maxlen:
        fmt += "%%-%ds   " % l
    if title:
        cli_out(fmt % tuple(title))
    for row in data:
        cli_out(fmt % tuple(row))
