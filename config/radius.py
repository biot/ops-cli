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
    radius_keys = (
        ('passkey', 'key'),
        ('udp_port', 'auth_port'),
        ('priority', 'priority'),
        ('retries', 'retries'),
        ('timeout', 'timeout'),
    )
    results = ovsdb.get('Radius_Server')
    for row in results:
        host = row['ip_address']
        line = "radius-server %s" % host
        for key, word in radius_keys:
            val = row.get(key)
            if val:
                lines.append(line + " %s %s" % (word, val))
    return lines
