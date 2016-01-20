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
from opscli.tokens import *
from opscli.options import *
from opscli.output import *


class Logrotate(Command):
    '''Configure log rotation policy'''
    command = 'logrotate'
    options = (
        Opt_all_order(
            ('maxsize', 'Maximum file size for rotation'),
            TInteger(min_int=1, max_int=200, help_text="File size in MiB"),
        ),
        Opt_all_order(
            ('period', 'Rotation period'),
            TString(
                ('hourly', 'Rotate log files every hour'),
                ('weekly', 'Rotate log files every week'),
                ('monthly', 'Rotate log files every month'),
            ),
        ),
    )

    def run(self, opts, flags):
        if not opts:
            raise Exception(CLI_ERR_INCOMPLETE)
        maxsize = period = None
        while opts:
            if opts[0] == 'maxsize':
                maxsize = opts[1].value
                opts = opts[2:]
            elif opts[0] == 'period':
                period = opts[1].value
                opts = opts[2:]
        if maxsize:
            # TODO write to OVSDB
            cli_out("<should write maxsize to OVSDB>")
        if period:
            # TODO write to OVSDB
            cli_out("<should write period to OVSDB>")


register_commands((Logrotate,), tree='config')
