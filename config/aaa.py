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
    'AAA_RADIUS': 'false',
    'AAA_FALLBACK': 'true',
    'SSH_AUTH_PASS': 'enable',
    'SSH_AUTH_PUBKEY': 'enable',
}


def generate_cli():
    lines = []
    results = ovsdb.get_map('System', column='aaa')
    aaa_config = (
        (
            'radius',
            'AAA_RADIUS',
            'aaa authentication login radius'
        ),
        (
            'fallback',
            'AAA_FALLBACK',
            'aaa authentication login fallback error local'
        ),
        (
            'ssh_passkeyauthentication',
            'SSH_AUTH_PASS',
            'no ssh password-authentication'
        ),
        (
            'ssh_publickeyauthentication',
            'SSH_AUTH_PUBKEY',
            'no ssh public-key-authentication'
        ),
    )
    for key, default, word in aaa_config:
        val = results.get(key)
        if val and val != DEFAULTS[default]:
            lines.append(word)

    return lines
