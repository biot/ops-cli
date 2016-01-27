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
from opscli.output import *
from opscli.context import *


class Quit(Command):
    '''Quit shell'''
    command = 'quit'

    def run(self, opts, flags):
        return False


register_commands((Quit,))


class Exit(Command):
    '''Exit current mode and down to previous mode'''
    command = 'exit'

    def run(self, opts, flags):
        if not context_pop():
            return False


class Pwc(Command):
    '''Show current configuration context'''
    command = 'pwc'

    def run(self, opts, flags):
        indent = 0
        for ctx_name in context_names()[1:]:
            context = context_get(ctx_name)
            cli_wrt(' ' * indent * 2)
            cli_wrt(context.name)
            if context.obj is not None:
                cli_wrt(' ' + str(context.obj))
            cli_out()
            indent += 1


register_commands((Pwc,), 'global')
