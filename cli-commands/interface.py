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
from opscli.options import *
from opscli.flags import *
from opscli.context import *


class Shutdown(Command):
    '''Disable the interface'''
    command = 'shutdown'
    flags = (F_NO,)

    def run(self, opts, args):
        cli_out("shutdown!")
        cli_out(opts)


register_commands((Shutdown,), tree='interface')


class Interface(Command):
    '''Select an interface to configure'''
    command = 'interface'
    options = (
        Opt_one(
            TInterface(help_text='Interface name'),
            ('lag', 'Configure link-aggregation parameters'),
            ('mgmt', 'Configure management interface'),
            ('vlan', 'VLAN configuration'),
        ),
    )

    def run(self, opts, flags):
        if isinstance(opts[0], TInterface):
            context_push('interface', obj=opts[0])


register_commands((Interface,), tree='config')
