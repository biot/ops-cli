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
'''
This module provides access to network interfaces.
'''

import opscli.ovsdb as ovsdb

intf_keys = [
    'admin_state', 'link_state', 'link_speed', 'link_resets',
    'duplex', 'mac_in_use'
]

mgmt_intf_keys = [
    'link_state', 'ip', 'subnet_mask', 'default_gateway',
    'ipv6_linklocal'
]


def get_interface_list():
    intflist = []
    response = ovsdb.get('Interface', columns=['name'])
    for row in response:
        intflist.append(row['name'])
    return intflist


def get_interface(intf):
    data = {}
    if intf == 'mgmt':
        results = ovsdb.get('System', columns=['mgmt_intf_status'])
        for key, value in results[0]['mgmt_intf_status'][1]:
            if key in mgmt_intf_keys:
                data[key] = value
        data['ip'] += '/' + data['subnet_mask']
        data.pop('subnet_mask')
    else:
        conditions = [['name', '==', str(intf)]]
        results = ovsdb.get('Interface', conditions=conditions)[0]
        for key in intf_keys:
            if key in results:
                data[key] = results[key]
        # Transceiver information.
        for key, value in results['hw_intf_info'][1]:
            data[key] = value

    return data
