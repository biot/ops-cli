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
    columns = ['id', 'admin']
    rows = ovsdb.get('VLAN', columns)
    lines = []
    vlans = {}
    for row in rows:
        vlan_id = int(row['id'])
        vlans[vlan_id] = row['admin']
    for vlan_id in sorted(vlans):
        lines.append("vlan %s" % vlan_id)
        if vlans[vlan_id] == 'up':
            lines.append("\tno shutdown")

    return lines
