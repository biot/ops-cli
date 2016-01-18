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


class Str_help(str):
    'String with associated help text.'

    def __init__(self, string):
        if isinstance(string, tuple):
            self.string, self.help_text = string
        else:
            self.string = string
            self.help_text = ''

    def __new__(cls, string):
        if isinstance(string, tuple):
            return super(Str_help, cls).__new__(cls, string[0])
        else:
            return super(Str_help, cls).__new__(cls, string)
