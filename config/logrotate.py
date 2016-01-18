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

# TODO
import opscli.ovsdb as ovsdb

# TODO should be a global facility
DEFAULTS = {
    'LOGROTATE_MAXSIZE': '10',
    'LOGROTATE_PERIOD': 'daily',
    'LOGROTATE_TARGET': 'local',
}


def generate_cli():
    lines = []
    results = ovsdb.get_map('System', column='logrotate_config')
    logrotate_config = (
        ['period', 'LOGROTATE_PERIOD', 'period'],
        ['maxsize', 'LOGROTATE_MAXSIZE', 'maxsize'],
        ['target', 'LOGROTATE_TARGET', 'target'],
    )
    for key, default, word in logrotate_config:
        val = results.get(key)
        if val and val != DEFAULTS[default]:
            lines.append("logrotate %s %s" % (word, val))

    return lines
