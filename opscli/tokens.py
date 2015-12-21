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

from copy import deepcopy

from opscli.stringhelp import Str_help
from ops.interface import get_interface_list

# Arguments that can be specified in any token instantiation.
global_args = ('required', 'help_text')


def check_arg_keys(kwargs, check_args):
    allowed = global_args + check_args
    for key in kwargs:
        if key not in allowed:
            raise ValueError


class Token(object):
    def __init__(self, **kwargs):
        self.required = kwargs.get('required', False)
        self.help_text = kwargs.get('help_text', '')
        self.value = None

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, str(self.value))

    def __eq__(self, word):
        return word == self.value

    def nailedcopy(self, word):
        new_token = deepcopy(self)
        new_token.parent = self
        new_token.nail(word)
        return new_token


class TKeyword(Token):
    def __init__(self, *args, **kwargs):
        Token.__init__(self, **kwargs)
        if len(args) > 1:
            raise TypeError('only one keyword can be declared at a time')
        self.word = Str_help(args[0])

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, str(self.word))

    def nail(self, word):
        if not self.verify(word):
            raise ValueError("invalid keyword")
        self.value = self.word

    def enum(self):
        return [self.word]

    def complete(self, word):
        if self.word.startswith(word):
            return [self.word]
        else:
            return []

    def syntax(self):
        return [self.word]

    def verify(self, word):
        # Must match the declared keyword, or at least complete to it.
        return self.word.startswith(word)


class TString(Token):
    def __init__(self, *args, **kwargs):
        Token.__init__(self, **kwargs)
        self.allowed = []
        for arg in args:
            if not isinstance(arg, str) and not isinstance(arg, tuple):
                raise TypeError('only strings (and help) are allowed')
            self.allowed.append(Str_help(arg))

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, str(self.allowed))

    def nail(self, word):
        for al in self.allowed:
            if al.startswith(word):
                self.value = al
                return
        raise ValueError("invalid string")

    def enum(self):
        return self.allowed

    def complete(self, word):
        results = []
        for al in self.allowed:
            if al.startswith(word):
                results.append(al)
        return results

    def verify(self, word):
        for al in self.allowed:
            if al.startswith(word):
                return True
        return False

    def syntax(self):
        return self.allowed


class TInteger(Token):
    def __init__(self, **kwargs):
        Token.__init__(self, **kwargs)
        check_arg_keys(kwargs, ('min_int', 'max_int'))
        self.min_int = kwargs.get('min_int')
        self.max_int = kwargs.get('max_int')

    def nail(self, word):
        if not self.verify(word):
            raise ValueError("invalid integer")
        self.value = int(word)

    def enum(self):
        if self.min_int is not None and self.max_int is not None:
            return range(self.min_int, self.max_int + 1)
        else:
            return []

    def complete(self, word):
        e_list = self.enum()
        if not e_list:
            return []
        results = []
        for e in e_list:
            if str(e).startswith(word):
                results.append(str(e))
        return results

    def verify(self, word):
        # Just needs to be a digit and, if a range limit is set, fall within.
        if not word.isdigit():
            return False
        value = int(word)
        if self.min_int is not None and value < self.min_int:
            return False
        if self.max_int is not None and value > self.max_int:
            return False
        return True

    def syntax(self):
        if self.min_int is not None and self.max_int is not None:
            summary = "%d-%d" % (self.min_int, self.max_int)
        else:
            summary = '<number>'
        return [Str_help((summary, self.help_text))]


class TInterface(Token):
    description = 'Interface name'

    def __init__(self, **kwargs):
        Token.__init__(self, **kwargs)
        if not self.help_text:
            self.help_text = 'Interface name'

    def nail(self, word):
        if word not in self.enum():
            raise ValueError("invalid interface")
        self.value = word

    def enum(self):
        return get_interface_list()

    def complete(self, word):
        e_list = self.enum()
        if not e_list:
            return []
        results = []
        for e in e_list:
            if e.startswith(word):
                results.append(e)
        return results

    def verify(self, intf):
        return intf in self.enum()

    def syntax(self):
        return [Str_help(('<interface>', self.help_text))]
