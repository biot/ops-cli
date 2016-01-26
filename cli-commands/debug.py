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
from opscli.options import *
from opscli.output import *
from opscli.debug import *


class Debug(Command):
    '''Enable debug output for subsystems'''
    command = 'debug'
    options = (
        Opt_one(*debug_available()),
    )
    flags = (F_NO, )

    def run(self, opts, flags):
        if not opts:
            raise Exception(CLI_ERR_INCOMPLETE)
        full_list = debug_available()
        for key in opts:
            if F_NO in flags:
                debug_disable(str(key))
            else:
                debug_enable(str(key))


class Show_debug(Command):
    '''Show current debug setting'''
    command = 'show debug'

    def run(self, opts, flags):
        for key in debug_enabled():
            cli_out(key)


register_commands((Debug, Show_debug), tree='global')
