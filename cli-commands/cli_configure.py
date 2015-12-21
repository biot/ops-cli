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

from opscli.cli import Command
from opscli.options import Opt_one
from opscli.output import *


class Configure(Command):
    '''Configuration from CLI'''
    command = 'configure'
    options = (
        Opt_one(
            ('terminal', 'Configure from terminal'),
            required=True,
        ),
    )
    # Only from top level context.
    context = [None]

    def run(self, opts, flags):
        if not opts:
            raise Exception(CLI_ERR_INCOMPLETE)
        self.cli.context_push('config')


class Exit(Command):
    '''Exit current mode and down to previous mode'''
    command = 'exit'

    def run(self, opts, flags):
        if self.cli.context:
            self.cli.context_pop()
        else:
            return False


commands = (Configure, Exit)
