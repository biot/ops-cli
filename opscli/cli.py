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

import sys
import os
from collections import OrderedDict

from pyrepl.reader import Reader
from pyrepl.unix_console import UnixConsole
from pyrepl.historical_reader import HistoricalReader
import pyrepl.commands

from opscli.command import *
from opscli.context import *
from opscli.stringhelp import Str_help
from opscli.flags import *
from opscli.output import *
from opscli.tokens import *
from opscli.options import *
import opscli.ovsdb as ovsdb
from opscli.debug import logline, debug_is_on
from stdcmd import Exit


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

        # Initialize command tree.
        for path in command_module_paths:
            if not os.path.isdir(path):
                cli_warn("Ignoring invalid module path '%s'." % path)
                continue
            self.load_commands(path)
        self.fixup_contexts()
        context_push('root')
        if debug_is_on('cli'):
            context_get().cmdtree.dump_tree()

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

    def load_commands(self, path):
        sys.path.insert(0, path)
        for filename in os.listdir(path):
            if filename[-3:] != '.py':
                continue
            # Strip '.py'.
            __import__(filename[:-3])

    def fixup_contexts(self):
        '''Add exit command to every non-root command tree.'''
        trees = list_cmdtrees()
        for tree in trees:
            if tree == 'root':
                continue
            register_commands((Exit,), tree=tree)

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
                    if DEBUG_TRACEBACK:
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
        cmdtree = context_get().cmdtree
        if words:
            matches = self.find_command(cmdtree, words)
            if not matches:
                raise Exception(CLI_ERR_NOMATCH)
            if line[-1].isspace():
                # Last character is a space, so whatever comes before has
                # to match a command unambiguously if we are to continue.
                if len(matches) != 1:
                    raise Exception(CLI_ERR_AMBIGUOUS)

                cmd_complete = False
                cmdobj = matches[0]
                for key in cmdobj.branch:
                    items.append(self.helpline(cmdobj.branch[key], words))
                if hasattr(cmdobj, 'options'):
                    opt_words = words[len(cmdobj.command):]
                    if not opt_words and F_NO_OPTS_OK in cmdobj.flags:
                        # Didn't use any options, but that's ok.
                        cmd_complete = True
                    elif len(opt_words) == len(cmdobj.options):
                        # Used all options, definitely a complete command.
                        cmd_complete = True
                    elif opt_words:
                        # Only some options were used, check if we missed
                        # any required ones.
                        try:
                            opt_tokens = tokenize_options(opt_words,
                                                          cmdobj.options)
                            check_required_options(opt_tokens, cmdobj.options)
                            # Didn't bomb out, so all is well.
                            cmd_complete = True
                        except:
                            pass
                    items.extend(help_options(cmdobj, words))
                else:
                    # Command has no options.
                    cmd_complete = True
                if cmd_complete and hasattr(cmdobj, 'run'):
                    items.insert(0, Str_help(('<cr>', cmdobj.__doc__)))
            else:
                # Possibly incomplete match, not ending in space.
                for cmdobj in matches:
                    if len(words) <= len(cmdobj.command):
                        # It's part of the command
                        items.append(self.helpline(cmdobj, words[:-1]))
                    else:
                        # Must be an option.
                        items.extend(complete_options(cmdobj, words))
        else:
            # On empty line: show all commands in this context.
            for key in cmdtree.branch:
                items.append(self.helpline(cmdtree.branch[key]))
            try:
                global_tree = get_cmdtree('global')
                for key in global_tree.branch:
                    items.append(self.helpline(global_tree.branch[key]))
            except ValueError:
                pass

        return sorted(items)

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
        cmdtree = context_get().cmdtree
        matches = self.find_command(cmdtree, words)
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
                items = help_options(cmdobj, words)
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
                    cmpls = complete_options(matches[0], words)
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

    def error(self, msg):
        '''This gets messages from pyrepl's edit commands, nothing you
        want to see displayed. However they're the sort of thing that
        cause readline to send a beep.'''
        self.console.beep()

    def make_prompt(self):
        cur_context = context_get()
        if cur_context.prompt is not None:
            context_string = "(%s)" % cur_context.prompt
        else:
            context_string = ''
            for ctx_name in context_names()[1:]:
                context_string += "(%s)" % ctx_name
        prompt = self.prompt_base + context_string + PROMPT_CHAR
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
            matches.append(cmdobj)
            return matches
        for key in cmdobj.branch:
            if key.startswith(words[0]):
                # word is a partial match for this command.
                if len(words) == 1:
                    # Found a match on all words.
                    last = cmdobj.branch[key]
                    matches.append(last)
                else:
                    # Continue matching on this branch with the next word.
                    return self.find_partial_command(cmdobj.branch[key],
                                                     words[1:], matches)
        return matches

    def find_command(self, cmdobj, words):
        matches = self.find_partial_command(cmdobj, words, [])

        if not matches:
            # Try the 'global' command tree as a last resort.
            try:
                global_tree = get_cmdtree('global')
                matches = self.find_partial_command(global_tree, words, [])
            except ValueError:
                pass

        return matches

    def run_command(self, words):
        if words[0] == 'help':
            self.show_help(words[1:])
            return True

        flags = []
        # Negated commands are in the tree without the leading 'no'.
        if words[0] == 'no':
            words.pop(0)
            flags.append(F_NO)

        cmdtree = context_get().cmdtree
        matches = self.find_command(cmdtree, words)
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
        lines.append(self.helpline(cmdobj))
        return lines

    def show_help(self, words):
        cmdtree = context_get().cmdtree
        if not words:
            items = []
            for key in cmdtree.branch:
                items.extend(self.get_help_subtree(cmdtree.branch[key]))
            cli_help(items)
        else:
            matches = self.find_command(cmdtree, words)
            if len(matches) == 0:
                cli_err(CLI_ERR_NOHELP_UNK)
            elif len(matches) > 1:
                cli_err(CLI_ERR_AMBIGUOUS)
            else:
                cli_out(matches[0].__doc__)
