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

import config.cli

from opscli.command import *
from opscli.output import *


INDENT = ' ' * 4

# Order in which subsystem config is generated.
subsystems = (
    'global',
    'lldp',
    'lacp',
    'logrotate',
    'aaa',
    'radius',
    'vlan',
)


class Show_running_config(Command):
    '''Current running configuration'''
    command = 'show running-configuration'

    def run(self, opts, flags):
        lines = config.cli.generate_config()
        for line in lines:
            line = line.replace('\t', INDENT)
            cli_out(line)


register_commands((Show_running_config,), tree='global')
