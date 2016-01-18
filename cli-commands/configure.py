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
from opscli.context import *
from opscli.options import Opt_one
from opscli.flags import *
from opscli.output import *

from vlan import Conf_vlan


class Configure(Command):
    '''Configuration from CLI'''
    command = 'configure'
    flags = (F_NO_OPTS_OK,)
    options = (
        Opt_one(
            ('terminal', 'Configure from terminal'),
        ),
    )
    # Only from top level context.
    context = [None]

    def run(self, opts, flags):
        context_push('config')


register_commands((Configure,))
