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
from collections import OrderedDict

from pyrepl.reader import Reader
from pyrepl.unix_console import UnixConsole
from pyrepl.historical_reader import HistoricalReader
import pyrepl.commands

from opscli.output import *
from opscli.tokens import Token, TKeyword
import opscli.ovsdb as ovsdb
from opscli.debug import logline, debug_is_on

HISTORY_FILE = '~/.opscli_history'
# Number of lines to remember across sessions.
HISTORY_SIZE = 1000
DEBUG_TRACEBACK = False


def dbg(msg):
    logline('cli', msg)


class Opscli(HistoricalReader):
    '''
    This class extends pyrepl's Reader to provide command modules.
    '''
    def __init__(self, ovsdb_server, command_module_paths=None):
        super(Opscli, self).__init__(UnixConsole())
        # Initialize the OVSDB helper.
        ovsdb.Ovsdb(server=ovsdb_server)
        self.motd = CLI_MSG_MOTD
        self.prompt_base = 'Openswitch'
        try:
            # TODO shell hangs before prompt if this is down
            results = ovsdb.get_map('System', column='mgmt_intf_status')
            if 'hostname' in results:
                self.prompt_base = results['hostname']
        except Exception as e:
            cli_err("Unable to connect to %s: %s." % (ovsdb_server, str(e)))
            raise Exception
        self.context = []
        # Top of the command tree.
        self.cmdtree = Command()
        self.cmdtree.command = ('root', )
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
            self.dump_tree(self.cmdtree)
        self.init_qhelp()
        self.init_completion()
        self.init_history()

    def init_qhelp(self):
        class rdr_qhelp(pyrepl.commands.Command):
            # Make Opscli instance available at Reader key callback time.
            cli = self
            def do(self):
                line = ''.join(self.reader.buffer)
                cli_wrt('\r\n')
                try:
                    items = self.cli.qhelp(line)
                    cli_help(items, end='\r\n')
                except Exception as e:
                    cli_wrt(str(e) + '\r\n')
                cli_wrt(self.cli.make_prompt())
                cli_wrt(line)
        self.bind(r'?', 'qhelp')
        self.commands['qhelp'] = rdr_qhelp

    def qhelp(self, line):
        '''Called when ? is pressed. line is the text up to that point.
        Returns help items to be shown, as a list of (command, helptext).'''
        items = []
        words = line.split()
        if words:
            matches = self.find_partial_command(self.cmdtree, words, [])
            if not matches:
                raise Exception(CLI_ERR_NOMATCH)
            if line[-1].isspace():
                # Last character is a space, to treat any match as a
                # definite target.
                if len(matches) == 1:
                    # Unambiguous match: show possible arguments with
                    # matching command stripped.
                    cmdobj = matches[0]
                    for key in cmdobj.branch:
                        items.append(self.helpline(cmdobj.branch[key], words))
                    if not items:
                        # Command is complete.
                        if hasattr(cmdobj, 'run'):
                            items.append(('<cr>', ''))
                else:
                    # More than one match on a definite target.
                    raise Exception(CLI_ERR_AMBIGUOUS)
            else:
                # Possibly incomplete match, not ending in space.
                for cmdobj in matches:
                    items.append(self.helpline(cmdobj))
        else:
            for key in self.cmdtree.branch:
                items.extend(self.get_help_subtree(self.cmdtree.branch[key]))

        return items

    def init_completion(self):
        class rdr_complete(pyrepl.commands.Command):
            # Make Opscli instance available at Reader key callback time.
            cli = self
            def do(self):
                line = ''.join(self.reader.buffer)
                try:
                    self.cli.complete(line)
                except Exception as e:
                    cli_wrt(str(e) + '\r\n')
        self.bind(r'\t', 'complete')
        self.commands['complete'] = rdr_complete

    def complete(self, line):
        if not line:
            return
        words = line.split()
        matches = self.find_partial_command(self.cmdtree, words, [])
        if not matches:
            return
        items = []
        if line[-1].isspace():
            if len(matches) != 1:
                # The line doesn't add up to an unambiguous command.
                return
            # We have matching words, and only need to list arguments.
            items = matches[0].branch.keys()
            if not items:
                # No more command branches off of this one. Maybe it
                # has some options?
                items = matches[0].options
        else:
            # Completing a word.
            if len(matches) == 1:
                # Found exactly one completion.
                cmpl_word = matches[0].command[len(words) -1]
                cmpl = cmpl_word[len(words[-1]):]
                self.insert(cmpl + ' ')
            else:
                # More than one match. Ignore the first completion attempt,
                # and list all possible completions on every tab afterwards.
                if self.last_event == 'complete':
                    for cmdobj in matches:
                        items.append(' '.join(cmdobj.command))
        if items:
            self.inline(fmt_cols(items))

    def after_command(self, cmd):
        # This has the callback names e.g. 'qhelp', 'complete' etc.
        self.last_event = cmd.event_name
        super(Opscli, self).after_command(cmd)

    def init_history(self):
        histfile = os.path.expanduser(HISTORY_FILE)
        if os.path.exists(histfile):
            self.history = open(histfile).read().split('\n')[:-1]

    def inline(self, text):
        '''Write text on the next line and reproduce the prompt and entered
        text without submitting it.'''
        cli_wrt('\r\n')
        cli_wrt(text.replace('\n', '\r\n'))
        cli_wrt('\r\n')
        cli_wrt(self.make_prompt())
        cli_wrt(''.join(self.buffer))

    def helpline(self, cmdobj, prefix=None):
        if prefix:
            words = cmdobj.command[len(prefix):]
        else:
            words = cmdobj.command
        return (' '.join(words), cmdobj.__doc__)

    def check_module(self, module):
        if not hasattr(module, 'commands'):
            raise Exception("no command set defined")
        if not isinstance(module.commands, tuple):
            raise Exception("invalid command set")
        for obj in module.commands:
            if (not hasattr(obj, 'command') or
                    not isinstance(obj.command, str)):
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
        cur = self.cmdtree
        for word in cmdclass.command.split():
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
        new_cmd = prev.add_child(word, cmdclass())
        # Provide the Command instance with this CLI instance.
        new_cmd.cli = self

    # DEBUG
    def dump_tree(self, cmdobj, level=0):
        dbg("%s%s %s %s" % ('    ' * level, ' '.join(cmdobj.command),
                            cmdobj.options, cmdobj.flags))
        for cmd in cmdobj.branch:
            self.dump_tree(cmdobj.branch[cmd], level + 1)

    def error(self, msg):
        '''This gets messages from pyrepl's edit commands, nothing you
        want to see displayed. However they're the sort of thing that
        cause readline to send a beep.'''
        self.console.beep()

    def context_push(self, ctx):
        self.context.append(ctx)

    def context_pop(self):
        self.context.pop()

    def make_prompt(self):
        if self.context:
            context = "(%s)" % self.context[-1]
            prompt_mode = PROMPT_WRITE
        else:
            context = ''
            prompt_mode = PROMPT_READ
        prompt = self.prompt_base + context + prompt_mode
        return prompt

    def start_shell(self):
        cli_out(self.motd)
        while True:
            try:
                while True:
                    self.ps1 = self.make_prompt()
                    line = self.readline()
                    if not self.process_line(line):
                        # Received quit, ctrl-d etc.
                        break
                break
            except EOFError:
                # ctrl-d quits the shell.
                break
            except KeyboardInterrupt:
                # ctrl-c throws away the current line and prompts again.
                cli_out('^C')
        # Save this session's history.
        histfile = os.path.expanduser(HISTORY_FILE)
        f = open(histfile, 'w')
        f.write('\n'.join(self.history[-HISTORY_SIZE:]))
        f.write('\n')
        f.close()

    def process_line(self, line):
        words = line.split()
        dbg(words)
        if words:
            try:
                if words == ['quit']:
                    return False
                else:
                    return self.run_command(words)
            except Exception as e:
                if DEBUG_TRACEBACK:
                    raise
                else:
                    cli_err(str(e))
        return True

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
            raise Exception(CLI_ERR_BADOPTION + "%s." % words[opts.index(None)])

        return opts

    def run_command(self, words):
        if words[0] == 'help':
            self.show_help(words[1:])
            return True

        flags = []
        # Negated commands are in the tree without the leading 'no'.
        if words[0] == 'no':
            flags.append(words.pop(0))

        matches = self.find_partial_command(self.cmdtree, words, [])
        if len(matches) == 0 or len(matches) > 1:
            # Either nothing matched, or more than one command matched.
            raise Exception(CLI_ERR_NOCOMMAND)
        cmdobj = matches.pop()

        if not hasattr(cmdobj, 'run'):
            # Dummy command node, such as 'show'.
            raise Exception(CLI_ERR_INCOMPLETE)

        opts = []
        if len(cmdobj.command) != len(words):
            # Some of the words aren't part of the command. The rest must
            # be options.
            opt_words = words[len(cmdobj.command):]
            opts = self.convert_options(cmdobj.options, opt_words)

        for flag in flags:
            if flag not in cmdobj.flags:
                # Something was flagged, but the command doesn't allow it.
                raise Exception(CLI_ERR_NOCOMMAND)
        try:
            # Run command.
            cmdobj.run(opts, flags)
        except Exception as e:
            if DEBUG_TRACEBACK:
                raise
            else:
                cli_err(str(e))

        return True

    def get_help_subtree(self, cmdobj):
        lines = []
        # Only show real entries in the tree.
        if hasattr(cmdobj, 'run'):
            lines.append(self.helpline(cmdobj))
        for key in cmdobj.branch:
            lines.extend(self.get_help_subtree(cmdobj.branch[key]))
        return lines

    def show_help(self, words):
        if not words:
            items = []
            for key in self.cmdtree.branch:
                items.extend(self.get_help_subtree(self.cmdtree.branch[key]))
            cli_help(items)
        else:
            matches = self.find_partial_command(self.cmdtree, words, [])
            if len(matches) == 0:
                cli_err(CLI_ERR_NOHELP_UNK)
            elif len(matches) > 1:
                cli_err(CLI_ERR_AMBIGUOUS)
            else:
                cli_out(matches[0].__doc__)


# parent class for a command.
class Command:
    '''No help provided.'''

    def __init__(self):
        self.cli = None
        self.branch = OrderedDict()
        if hasattr(self, 'command'):
            self.command = tuple(self.command.split())
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
            cmdobj.command = (word,)
        return cmdobj
