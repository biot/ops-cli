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
    results = ovsdb.get('Interface')
    for row in results:
        intf = []
        for key, value in row['other_config'][1]:
            if key == 'lldp_enable_dir':
                if value == 'off' or value.find('rx') == -1:
                    intf.append("\tno lldp reception")
                if value == 'off' or value.find('tx') == -1:
                    intf.append("\tno lldp transmission")
        if intf:
            lines.append("interface %s" % row['name'])
            lines.extend(intf)

    return lines
