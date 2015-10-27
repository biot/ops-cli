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

_debug_keys = (
    'cli',
    'ovsdb'
)

_dbg_enabled = {}


def debug_available():
    return sorted(_debug_keys)


def debug_enabled():
    return sorted(_dbg_enabled.keys())


def debug_enable(key):
    if key not in _debug_keys:
        raise Exception("Invalid debug key")
    _dbg_enabled[key] = True


def debug_disable(key):
    if key not in _debug_keys:
        raise Exception("Invalid debug key")
    _dbg_enabled.pop(key, None)


def debug_disable_all():
    _dbg_enabed.clear()


def debug_is_on(key):
    return key in _dbg_enabled


def logline(key, msg):
    if key in _dbg_enabled:
        print "DBG: %s: %s" % (key, msg)
