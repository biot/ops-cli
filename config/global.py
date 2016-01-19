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

# TODO
import opscli.ovsdb as ovsdb


def generate_cli():
    lines = []

    # hostname
    results = ovsdb.get_map('System', column='mgmt_intf_status')
    lines.append("hostname %s" % results.get('hostname', ''))

    # alias
    results = ovsdb.get('CLI_Alias', columns=['alias_name',
                        'alias_definition'])
    for row in results:
        lines.append("alias %s %s" % (row['alias_name'],
                     row['alias_definition']))

    return lines
