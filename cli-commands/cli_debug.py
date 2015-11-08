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

from opscli.output import cli_out
from opscli.cli import Command
from opscli.debug import debug_available, debug_enabled
from opscli.debug import debug_enable, debug_disable


class Debug(Command):
    '''Enable debug output for subsystems'''
    command = 'debug'
    options = tuple(debug_available())
    flags = ('no', )

    def run(self, opts, flags):
        if not opts:
            raise Exception("incomplete command")
        full_list = debug_available()
        for key in opts:
            if key not in full_list:
                raise Exception("invalid debug option '%s'" % key)
        for key in opts:
            if 'no' in flags:
                debug_disable(str(key))
            else:
                debug_enable(str(key))


class Show_debug(Command):
    '''Show current debug setting'''
    command = 'show debug'

    def run(self, opts, flags):
        for key in debug_enabled():
            cli_out(key)


commands = (Debug, Show_debug)
