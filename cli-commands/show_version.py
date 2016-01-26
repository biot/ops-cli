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
from opscli.options import *
from opscli.tokens import *


class Show_version(Command):
    '''Version information'''
    command = 'show version'
    options = (
        Opt_one(
            ('hardware', 'Hardware information'),
            ('software', 'Software information'),
            required=True,
        ),
    )

    def run(self, opts, flags):
        if 'hardware' in opts:
            cli_out('Hardware version 0.1')
        if 'software' in opts:
            cli_out('Software version 0.1')


class Set(Command):
    '''Set various things'''
    command = 'set'


class Set_protocol_version(Command):
    '''Set protocol version'''
    command = 'set protocol'
    options = (
        Opt_one(
            TInteger(min_int=1, max_int=5, help_text='Version to set'),
            required=True),
    )

    def run(self, opts, flags):
        cli_out("Setting protocol version %s" % opts[0])


register_commands((Show_version, Set, Set_protocol_version), tree='global')
