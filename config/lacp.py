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


def generate_cli():
    lines = []
    results = ovsdb.get_map('System', column='lacp_config')
    val = results.get('lacp-system-priority')
    if val:
        lines.append("lacp system-priority %s" % val)

    return lines
