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

from ops.interface import get_interface_list


class Token(object):
    '''Attributes:
        short       Short lowercase name for this token type.
        decription  Capitalized description.
        syntax      Syntax description e.g. <interface>
       Methods:
        enum        Returns a list of all possible values for this token.
        verify      Verify whether this is a valid name for this token.
    '''
    def __init__(self, name):
        if hasattr(self, 'verify') and not self.verify(name):
            raise Exception("invalid %s" % self.short)
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)

    def __eq__(self, item):
        return item == self.name


class TKeyword(Token):
    pass


class TString(Token):
    pass


class TInterface(Token):
    short = 'interface'
    description = 'Interface name'
    syntax = '<interface>'

    def enum(self):
        return get_interface_list()

    def verify(self, intf):
        return intf in self.enum()
