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

import sys
import os
from cmd import Cmd
import readline
from collections import OrderedDict

from opscli.output import cli_out, out_cols, cli_wrt, cli_warn, cli_err
from opscli.tokens import Token, TKeyword
import opscli.ovsdb as ovsdb
from opscli.debug import logline, debug_is_on

PROMPT_READ = '> '
PROMPT_WRITE = '# '
DEBUG_TRACEBACK = False

_builtin_commands = ('quit', 'EOF')


def dbg(msg):
    logline('cli', msg)


class Opscli(Cmd):
    '''
    This class extends Python's Cmd to provide command modules.
    '''
    def __init__(self, ovsdb_server, command_module_paths=None):
        Cmd.__init__(self)
        # Initialize the OVSDB helper.
        ovsdb.Ovsdb(server=ovsdb_server)
        self.motd = "OpenSwitch shell"
        self.base_prompt = 'Openswitch'
        try:
            results = ovsdb.get_map('System', column='mgmt_intf_status')
            if 'hostname' in results:
                self.base_prompt = results['hostname']
        except Exception as e:
            cli_err("Unable to connect to %s: %s." % (ovsdb_server, str(e)))
            raise Exception
        self.prompt_mode = PROMPT_READ
        self.prompt = self.base_prompt + self.prompt_mode
        # Top of the command tree.
        self.commands = Command()
        self.commands.command = ('root', )
        for path in command_module_paths:
            if not os.path.isdir(path):
                cli_warn("Ignoring invalid module path '%s'." % path)
                continue
            sys.path.insert(0, path)
            for filename in os.listdir(path):
                if filename[:4] != 'cli_' or filename[-3:] != '.py':
                    continue
                self.load_module(filename)
        if debug_is_on('cli'):
            self.dump_tree(self.commands)

    def check_module(self, module):
        if not hasattr(module, 'commands'):
            raise Exception("no command set defined")
        if not isinstance(module.commands, tuple):
            raise Exception("invalid command set")
        for obj in module.commands:
            if (not hasattr(obj, 'command') or
                    not isinstance(obj.command, tuple)):
                raise Exception("invalid definition for '%s'" % obj.__name__)

    def load_module(self, filename):
        modname = filename[:-3]
        module = __import__(modname)
        try:
            self.check_module(module)
        except Exception as e:
            dbg("Not loading module %s: %s." % (modname, e))
            return
        for cmdclass in module.commands:
            dbg("Adding command %s." % cmdclass.__name__)
            try:
                self.insert_command(cmdclass)
            except Exception as e:
                cli_err("failed to add command '%s': %s." % (cmdclass.__name__,
                        str(e)))

    def find_branch(self, cmdobj, word):
        if word in cmdobj.branch:
            return cmdobj.branch[word]

    # Instantiate a Command object in the right place in the command tree.
    def insert_command(self, cmdclass):
        prev = None
        cur = self.commands
        for word in cmdclass.command:
            branch = self.find_branch(cur, word)
            prev = cur
            if branch is not None:
                cur = branch
            else:
                # Instantiate dummy command object here.
                cur = cur.add_child(word, Command())
        if hasattr(cur, 'run'):
                raise Exception("duplicate command %s")
        # Replace dummy object with the new instantiated command.
        prev.add_child(word, cmdclass())

    # DEBUG
    def dump_tree(self, cmdobj, level=0):
        dbg("%s%s %s %s" % ('    ' * level, ' '.join(cmdobj.command),
                            cmdobj.options, cmdobj.flags))
        for cmd in cmdobj.branch:
            self.dump_tree(cmdobj.branch[cmd], level + 1)

    def start_shell(self):
        cli_out(self.motd)
        while True:
            try:
                Cmd.cmdloop(self)
                break
            except KeyboardInterrupt:
                # ctrl-c throws away the current line and prompts again
                cli_out('^C')

    def precmd(self, line):
        words = line.split()
        dbg(words)
        if len(words) == 1 and words[0] in _builtin_commands:
            return line
        if words:
            try:
                self.run_command(words)
            except Exception as e:
                if DEBUG_TRACEBACK:
                    raise
                else:
                    cli_err(str(e))
        self.prompt = self.base_prompt + self.prompt_mode
        return ''

    def emptyline(self):
        pass

    def do_quit(self, args):
        return True

    def do_EOF(self, args):
        cli_out('')
        return self.do_quit(None)

    # Traverse tree starting at cmdobj to find a command consisting of words.
    # returns Command object, or None if not found.
    # TODO Currently unused.
    def find_command(self, cmdobj, words):
        if words[0] in cmdobj.branch:
            if len(words) == 1:
                # Found a complete match on all words.
                return cmdobj.branch[words[0]]
            else:
                # Continue matching on this branch with the next word.
                return self.find_command(cmdobj.branch[words[0]], words[1:])
        else:
            # Didn't find the word. Stop searching and return what we have.
            return cmdobj

    # Traverse tree starting at cmdobj to find a command for which all words
    # are at least a partial match. Returns list of Command objects that match.
    def find_partial_command(self, cmdobj, words, matches):
        if len(cmdobj.branch) == 0:
            # This branch is a complete match for all words.
            matches.append(cmdobj)
            return matches
        for key in cmdobj.branch:
            if key.startswith(words[0]):
                # word is a partial match for this command.
                if len(words) == 1:
                    # Found a match on all words.
                    matches.append(cmdobj.branch[key])
                else:
                    # Continue matching on this branch with the next word.
                    return self.find_partial_command(cmdobj.branch[key],
                                                     words[1:], matches)
        return matches

    # Tokenize words to Token-derived types according to the given options
    # tuple, raising an exception for non-matching words.
    def convert_options(self, options, words):
        # Make a mutable copy for local use.
        options = list(options)
        opts = [None] * len(words)
        for w in range(len(words)):
            if words[w] in options:
                # Found a keyword.
                opts[w] = TKeyword(words[w])
            else:
                # Must be a non-keyword option.
                for option_type in options:
                    if isinstance(option_type, str):
                        continue
                    if not issubclass(option_type, Token):
                        # Bug in command module options list.
                        raise Exception("invalid command module option %s"
                                        % str(option_type))
                    # Instantiate a token for this option. This will bomb out
                    # with an exception if the token type's verify() fails.
                    opts[w] = option_type(words[w])
        if None in opts:
            # Something didn't get tokenized.
            raise Exception("invalid option %s" % words[opts.index(None)])

        return opts

    def run_command(self, words):
        if words[0] == 'help':
            if len(words) == 1:
                for key in self.commands.branch:
                    self.show_help_subtree(self.commands.branch[key])
            else:
                self.show_help(words[1:])
            return ''

        flags = []
        # Negated commands are in the tree without the leading 'no'.
        if words[0] == 'no':
            flags.append(words.pop(0))

        matches = self.find_partial_command(self.commands, words, [])
        if len(matches) == 0 or len(matches) > 1:
            # Either nothing matched, or more than one command matched.
            raise Exception("no such command")
        cmdobj = matches.pop()

        if not hasattr(cmdobj, 'run'):
            # Dummy command node, such as 'show'.
            raise Exception("incomplete command")

        opts = []
        if len(cmdobj.command) != len(words):
            # Some of the words aren't part of the command. The rest must
            # be options.
            opt_words = words[len(cmdobj.command):]
            opts = self.convert_options(cmdobj.options, opt_words)

        for flag in flags:
            if flag not in cmdobj.flags:
                # Something was flagged, but the command doesn't allow it.
                raise Exception("no such command")
        try:
            # Run command.
            cmdobj.run(opts, flags)
        except Exception as e:
            if DEBUG_TRACEBACK:
                raise
            else:
                cli_err(str(e))
        # Return to Cmd module as handled.
        return ''

    def complete(self, text, state):
        line = readline.get_line_buffer()
        if line:
            words = line.split()
            matches = self.find_partial_command(self.commands, words, [])
        else:
            # Empty line, get list of matches from the tree root.
            matches = [self.commands]
        if not line or line[-1].isspace():
            if len(matches) != 1:
                return None
            # We have matching words, and need to list what can follow them.
            cli_out('')
            out_cols(matches[0].branch)
            cli_wrt(self.prompt + line)
            completion = None
        else:
            if len(matches) < state + 1:
                # No more matches.
                return None
            completion = matches[state].command[len(words) - 1] + ' '
        return completion

    def show_help_subtree(self, cmdobj):
        # Skip dummy entries in the tree.
        if hasattr(cmdobj, 'run'):
            cmdstring = ' '.join([str(s) for s in cmdobj.command])
            cli_out("%-20s %s" % (cmdstring, cmdobj.__doc__))
        for key in cmdobj.branch:
            self.show_help_subtree(cmdobj.branch[key])

    def show_help(self, words):
        matches = self.find_partial_command(self.commands, words, [])
        if len(matches) == 0:
            cli_err("No help available: unknown command.")
        elif len(matches) > 1:
            cli_err("Ambiguous command.")
        else:
            cli_out(matches[0].__doc__)


# parent class for a command.
class Command:
    '''No help provided.'''

    def __init__(self):
        self.branch = OrderedDict()
        for attr in ('options', 'flags', 'context'):
            if not hasattr(self, attr):
                setattr(self, attr, tuple())

    def __repr__(self):
        return "<%s'>" % (self.__class__.__name__)

    def add_child(self, word, cmdobj):
        self.branch[word] = cmdobj
        if not hasattr(cmdobj, 'command'):
            # Add word as default command. Not really needed for tree
            # traversal, but completion uses it.
            cmdobj.command = (word, )
        return cmdobj
