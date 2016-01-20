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
from opscli.context import *
from opscli.output import *
import opscli.ovsdb as ovsdb


class Shutdown(Command):
    '''Disable the VLAN'''
    command = 'shutdown'
    flags = (F_NO,)

    def run(self, opts, args):
        cli_out("shutdown!")
        cli_out(opts)


register_commands((Shutdown,), tree='vlan')


class Conf_vlan(Command):
    '''VLAN configuration'''
    command = 'vlan'
    options = (
        Opt_one(
            TInteger(min_int=1, max_int=4095, help_text='VLAN identifier'),
            ('internal', 'VLAN internal configuration'),
            required=True,
        ),
    )

    def run(self, opts, flags):
        v = Vlan(opts[0])
        context_push('vlan', obj=v)


register_commands((Conf_vlan,), tree='config')


class Show_vlan(Command):
    '''Show VLAN configuration'''
    command = 'show vlan'
    flags = (F_NO_OPTS_OK,)
    options = (
        Opt_one(
            TInteger(min_int=1, max_int=4095, help_text='VLAN identifier'),
            ('internal', 'VLAN internal configuration'),
            ('summary', 'VLAN summary'),
        ),
    )

    def run(self, opts, flags):
        columns = ['id', 'name', 'oper_state', 'oper_state_reason']
        query = []
        if opts:
            if opts[0] == 'internal':
                self.show_vlan_internal()
                return
            elif isinstance(opts[0].value, int):
                query = [['id', '==', opts[0].value]]
        rows = ovsdb.get('VLAN', columns, query)
        if opts and opts[0] == 'summary':
            cli_out("Number of existing VLANs: %d" % len(rows))
        else:
            if opts and len(rows) == 0:
                cli_out("VLAN %d has not been configured." % opts[0].value)
            else:
                col_data = []
                for row in rows:
                    col = []
                    for name in columns:
                        col.append(str(row[name]))
                    col_data.append(col)
                out_table(col_data, title=['ID', 'Name', 'State', 'Reason'])

    def show_vlan_internal(self):
        data = ovsdb.get_map('System', 'other_config')
        cli_out("Internal VLAN range; %s-%s" % (
                data.get('min_internal_vlan', ''),
                data.get('max_internal_vlan', '')))
        cli_out("Internal VLAN policy: %s" % data.get('internal_vlan_policy',
                ''))
        cli_out("Assigned interfaces:")
        # TODO


register_commands((Show_vlan,))
