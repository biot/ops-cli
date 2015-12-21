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

from opscli.stringhelp import Str_help
from opscli.flags import *
from opscli.output import *
from opscli.tokens import Token, TKeyword
from opscli.options import Option, complete_options, help_options
from opscli.options import tokenize_options, check_required_options
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
        self.fix_syntax_table()
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
        self.init_ctrl_c()
        self.init_qhelp()
        self.init_completion()
        self.init_history()

    def fix_syntax_table(self):
        '''The default pyrepl syntax table only considers a-z as word
        boundaries, which affects keyboard navigation. Add a few more.'''
        extra = '0123456789_-'
        for c in extra:
            self.syntax_table[unichr(ord(c))] = 1

    def init_ctrl_c(self):
        class ctrl_c(pyrepl.commands.Command):
            def do(self):
                raise KeyboardInterrupt
        self.commands['interrupt'] = ctrl_c

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
                    raise
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
                # Last character is a space, so whatever comes before has
                # to match a command unambiguously if we are to continue.
                if len(matches) != 1:
                    raise Exception(CLI_ERR_AMBIGUOUS)

                cmdobj = matches[0]
                for key in cmdobj.branch:
                    items.append(self.helpline(cmdobj.branch[key], words))
                # Or maybe the command is complete, and has some options
                # that can come next.
                items.extend(help_options(cmdobj.options, words))
                if F_NO_OPTS_OK in cmdobj.flags:
                    # Command is complete by itself, too.
                    items.insert(0, Str_help(('<cr>', cmdobj.__doc__)))
            else:
                # Possibly incomplete match, not ending in space.
                for cmdobj in matches:
                    if len(words) <= len(cmdobj.command):
                        # It's part of the command
                        items.append(self.helpline(cmdobj, words[:-1]))
                    else:
                        # Must be an option.
                        items.extend(complete_options(cmdobj.options, words))
        else:
            # On empty line: show all top-level commands.
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
                    if DEBUG_TRACEBACK:
                        raise
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
            # Showing next possible words or arguments.
            if len(matches) != 1:
                # The line doesn't add up to an unambiguous command.
                return

            if self.last_event != 'complete':
                # Only show next words/arguments on second tab.
                return

            cmdobj = matches[0]
            # Strip matched command words.
            words = words[len(cmdobj.command):]

            if cmdobj.branch.keys():
                # We have some matching words, need to list the rest.
                items = cmdobj.branch.keys()
            else:
                # No more commands branch off of this one. Maybe it
                # has some options?
                items = help_options(cmdobj.options, words)
        else:
            # Completing a word.
            if len(matches) == 1:
                # Found exactly one completion.
                if len(words) <= len(matches[0].command):
                    # It's part of the command
                    cmpl_word = matches[0].command[len(words) - 1]
                else:
                    # Must be an option.
                    cmpl_word = None
                    cmpls = complete_options(matches[0].options, words)
                    if len(cmpls) == 1:
                        # Just one option matched.
                        cmpl_word = cmpls[0]
                    elif len(cmpls) > 1:
                        # More than one match. Ignore the first completion
                        # attempt, and list all possible completions on every
                        # tab afterwards.
                        if self.last_event == 'complete':
                            for cmdobj in matches:
                                items.append(' '.join(cmpls))
                if cmpl_word:
                    cmpl = cmpl_word[len(words[-1]):]
                    self.insert(cmpl + ' ')
            else:
                # More than one match. Ignore the first completion attempt,
                # and list all possible completions on every tab afterwards.
                if self.last_event == 'complete':
                    for cmdobj in matches:
                        items.append(' '.join(cmdobj.command))
        if items:
            self.print_inline(fmt_cols(items))

    def after_command(self, cmd):
        # This has the callback names e.g. 'qhelp', 'complete' etc.
        self.last_event = cmd.event_name
        super(Opscli, self).after_command(cmd)

    def init_history(self):
        histfile = os.path.expanduser(HISTORY_FILE)
        if os.path.exists(histfile):
            self.history = open(histfile).read().split('\n')[:-1]

    def print_inline(self, text):
        '''Write text on the next line, and reproduce the prompt and entered
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
        return Str_help((' '.join(words), cmdobj.__doc__))

    def check_module(self, module):
        if not hasattr(module, 'commands'):
            raise Exception("no command set defined")
        if not isinstance(module.commands, tuple):
            raise Exception("invalid command set")
        for obj in module.commands:
            if (not hasattr(obj, 'command') or
                    not isinstance(obj.command, str)):
                raise Exception("invalid definition for '%s'" % obj.__name__)
            if not hasattr(obj, 'options'):
                continue
            if not isinstance(getattr(obj, 'options'), tuple):
                raise Exception("options must be a tuple.")
            for opt in obj.options:
                if not issubclass(opt.__class__, Option):
                    raise Exception("invalid option %s" % str(opt))
                for arg in opt.args:
                    if isinstance(arg, str):
                        continue
                    if issubclass(arg.__class__, Token):
                        continue
                    raise Exception("invalid token for option %s: %s" % (
                        str(opt), str(arg)))

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
                cur = cur.add_child(word, Command(is_dummy=True))
        if hasattr(cur, 'run'):
                raise Exception("duplicate command %s")
        # Replace dummy object with the new instantiated command.
        new_cmd = prev.add_child(word, cmdclass())
        # Provide the Command instance with this CLI instance.
        new_cmd.cli = self

    def dump_tree(self, cmdobj, level=0):
        dbg("%s%s %s %s {%s...}" % ('    ' * level, ' '.join(cmdobj.command),
            cmdobj.options, cmdobj.flags, cmdobj.__doc__[:10]))
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

    def context_list(self):
        return self.context

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
            # TODO catch all exceptions, log traceback, print error msg
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

    # Traverse tree starting at cmdobj to find a command for which all words
    # are at least a partial match. Returns list of Command objects that match.
    def find_partial_command(self, cmdobj, words, matches):
        if len(cmdobj.branch) == 0:
            # This branch is a complete match for all words.
            if self.check_context(cmdobj):
                # This command is allowed in the current context.
                matches.append(cmdobj)
            # In any case we're done with this branch.
            return matches
        for key in cmdobj.branch:
            if key.startswith(words[0]):
                # word is a partial match for this command.
                if len(words) == 1:
                    # Found a match on all words.
                    last = cmdobj.branch[key]
                    if self.check_context(last):
                        matches.append(last)
                else:
                    # Continue matching on this branch with the next word.
                    return self.find_partial_command(cmdobj.branch[key],
                                                     words[1:], matches)
        return matches

    # TODO
    def check_context(self, cmdobj):
        return True
        #cli_wrt("{%s}{%s-%s} " % (self.context, ' '.join(cmdobj.command),
        #    cmdobj.context))
        '''Check command context specification against the running context.'''
        if not cmdobj.context:
            # An empty context means it can be run anywhere.
            return True

        if len(cmdobj.context) == 1 and cmdobj.context[0] is None:
            # Command specifically must not be called from anything
            # but the top level.
            return len(self.context) == 0


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

        tokens = []
        if len(cmdobj.command) != len(words):
            # Some of the words aren't part of the command. The rest must
            # be options.
            opt_words = words[len(cmdobj.command):]
            tokens = tokenize_options(opt_words, cmdobj.options)

        check_required_options(tokens, cmdobj.options)

        for flag in flags:
            if flag not in cmdobj.flags:
                # Something was flagged, but the command doesn't allow it.
                raise Exception(CLI_ERR_NOCOMMAND)
        try:
            # Run command.
            ret = cmdobj.run(tokens, flags)
        except Exception as e:
            if DEBUG_TRACEBACK:
                raise
            else:
                cli_err(str(e))
                return True

        # Most commands just return None, which is fine.
        return ret is not False

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

    def __init__(self, is_dummy=False):
        self.cli = None
        self.branch = OrderedDict()
        self.is_dummy = is_dummy
        if hasattr(self, 'command'):
            self.command = tuple(self.command.split())
        for attr in ('options', 'flags', 'context'):
            if not hasattr(self, attr):
                setattr(self, attr, tuple())

    def __repr__(self):
        name = "%s" % (self.__class__.__name__)
        if self.is_dummy:
            name += '(dummy)'
        return "<%s>" % name

    def add_child(self, word, cmdobj):
        if word in self.branch and self.branch[word].branch:
            # Child already exists, and has a branch going off of it.
            # It might still be a dummy, but that branch has to be kept.
            if cmdobj.branch:
                # Shouldn't happen.
                raise exception("dupe!")
            cmdobj.branch = self.branch[word].branch
        # Don't overwrite an existing branch, unless it was a dummy.
        if word not in self.branch or self.branch[word].is_dummy:
            self.branch[word] = cmdobj
        if not hasattr(cmdobj, 'command'):
            # Add word as default command. Not really needed for tree
            # traversal, but completion uses it.
            cmdobj.command = (word,)
        return cmdobj
