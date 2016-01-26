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

from collections import OrderedDict

from opscli.options import Option
from opscli.tokens import Token
from opscli.debug import logline

_command_trees = {}


def dbg(msg):
    logline('cli', msg)


def list_cmdtrees():
    return list(_command_trees)


def get_cmdtree(name):
    if name not in _command_trees:
        raise Exception("no command tree '%s'" % name)
    return _command_trees.get(name)


def register_commands(commands, tree='root'):
    if not isinstance(commands, tuple):
        raise Exception("commands must be in a tuple")
    if tree not in _command_trees:
        _command_trees[tree] = Command(tree)
    cmdtree = _command_trees[tree]
    for cmdclass in commands:
        try:
            cmdtree.insert_command(cmdclass)
        except Exception as e:
            raise Exception("failed to add command '%s': %s." % (
                            cmdclass.__name__, str(e)))

    return cmdtree


class Command:
    '''No help provided.'''

    def __init__(self, name='', is_dummy=False):
        self.cli = None
        self.branch = OrderedDict()
        self.is_dummy = is_dummy
        if hasattr(self, 'command'):
            self.command = tuple(self.command.split())
        else:
            self.command = (name,)
        for attr in ('options', 'flags', 'subcommands'):
            if not hasattr(self, attr):
                setattr(self, attr, tuple())

    def __repr__(self):
        name = "%s" % (self.__class__.__name__)
        if self.is_dummy:
            name += '(dummy)'
        return "<%s>" % name

    def dump_tree(self, cmdobj=None, level=0):
        if cmdobj is None:
            cmdobj = self
        dbg("%s%s %s %s {%s...}" % ('    ' * level, ' '.join(cmdobj.command),
            cmdobj.options, cmdobj.flags, cmdobj.__doc__[:10]))
        for cmd in cmdobj.branch:
            self.dump_tree(cmdobj.branch[cmd], level + 1)

    def check_command(self, cmdobj):
        if (not hasattr(cmdobj, 'command') or
                not isinstance(cmdobj.command, str)):
            raise Exception("invalid definition for '%s'" % cmdobj.__name__)
        if not hasattr(cmdobj, 'options'):
            return
        if not isinstance(getattr(cmdobj, 'options'), tuple):
            raise Exception("options must be a tuple.")
        for opt in cmdobj.options:
            if not issubclass(opt.__class__, Option):
                raise Exception("invalid option %s" % str(opt))
            for arg in opt.args:
                if isinstance(arg, str):
                    continue
                if issubclass(arg.__class__, Token):
                    continue
                raise Exception("invalid token for option %s: %s" % (
                    str(opt), str(arg)))

    def find_branch(self, cmdobj, word):
        if word in cmdobj.branch:
            return cmdobj.branch[word]

    # Instantiate a Command object in the right place
    def insert_command(self, cmdclass):
        self.check_command(cmdclass)
        dbg("adding %s:%s." % (self.command[0], cmdclass.__name__))
        prev = None
        cur = self
        for word in cmdclass.command.split():
            branch = self.find_branch(cur, word)
            prev = cur
            if branch is not None:
                cur = branch
            else:
                # Instantiate dummy command object here.
                cur = cur.add_child(word, Command(is_dummy=True))
        if hasattr(cur, 'run'):
                raise Exception("duplicate command %s")
        # Replace dummy object with the new instantiated command.
        new_cmd = prev.add_child(word, cmdclass())

    def add_child(self, word, cmdobj):
        if word in self.branch and self.branch[word].branch:
            # Child already exists, and has a branch going off of it.
            # It might still be a dummy, but that branch has to be kept.
            if cmdobj.branch:
                # Shouldn't happen.
                raise Exception("dupe!")
            cmdobj.branch = self.branch[word].branch
        # Don't overwrite an existing branch, unless it was a dummy.
        if word not in self.branch or self.branch[word].is_dummy:
            self.branch[word] = cmdobj
        if not hasattr(cmdobj, 'command'):
            # Add word as default command. Not really needed for tree
            # traversal, but completion uses it.
            cmdobj.command = (word,)
        return cmdobj
