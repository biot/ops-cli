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

from opscli.command import *
from opscli.flags import *
from opscli.tokens import *
from opscli.options import *
from opscli.output import *
from ops.interface import get_interface, get_interface_list


class Show_interface(Command):
    '''Interface information'''
    command = 'show interface'
    flags = (F_NO_OPTS_OK,)
    options = (
        Opt_one(
            TInterface(),
            ('mgmt', 'Management interface details'),
        ),
        Opt_one(
            ('brief', 'Show brief info of interfaces'),
            ('transceiver', 'Show transceiver info for interfaces'),
        ),
    )

    def run(self, opts, flags):
        keymap = 'interface'
        intf = None
        if opts:
            if isinstance(opts[0], TInterface):
                # "show interface <interface>"
                intf = opts[0]
            elif isinstance(opts[0], TKeyword):
                if opts[0] == 'mgmt':
                    # "show interface mgmt"
                    intf = opts[0]
                    keymap = 'mgmt-interface'
        if intf:
            intflist = [intf]
        else:
            intflist = get_interface_list()

        for intf in intflist:
            if 'transceiver' in opts:
                keymap = 'interface-transceiver'
            data = get_interface(intf)
            line = "Interface %s" % intf
            if 'brief' in opts:
                # Show only the interface + oper and admin state.
                if 'link_state' in data:
                    line += " is %s" % data['link_state']
                    if data['link_state'] == 'down' and 'admin_state' in data:
                        line += " (administratively %s)" % data['admin_state']
                cli_out(line)
            else:
                # Show all interface attributes in keymap.
                cli_out(line + ':')
                out_kv(keymap, data)


register_commands((Show_interface,), tree='global')
