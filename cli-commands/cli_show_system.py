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

from opscli.output import out_kv
from opscli.cli import Command
import opscli.ovsdb as ovsdb


class Show_system(Command):
    '''System information'''
    command = ('show', 'system')

    def run(self, opts, flags):
        data = ovsdb.get_map('Subsystem', 'other_info')
        out_kv('system', data)


class Show_system_fan(Command):
    '''Fan information'''
    command = ('show', 'system', 'fan')

    def run(self, opts, flags):
        data = ovsdb.get_map('Subsystem', 'other_config')
        out_kv('system-fan', data)


commands = (Show_system, Show_system_fan)
