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

from opscli.exceptions import *
from opscli.tokens import *
from opscli.output import *


def match_words(words, options):
    w = 0
    tokens = []
    for o in range(len(options)):
        m_tokens = options[o].match(words[w:])
        if not m_tokens:
            if options[o].required:
                raise Exception(CLI_ERR_AMBIGUOUS)
            continue
        # First matching option wins.
        tokens.extend(m_tokens)
        w += len(m_tokens)
        if w >= len(words):
            # Found tokens for all words.
            break

    return tokens


def complete_options(cmdobj, words):
    results = []
    for opt in cmdobj.options:
        # Get list of tokens that the last word can syntactically match.
        tokens = opt.next_token(words[:-1])
        if not tokens:
            continue
        if tokens[-1] is None:
            # Tokens before None are the *only* ones that can follow.
            results = opt.complete(tokens[:-1], words)
            break
        else:
            results.extend(opt.complete(tokens, words))

    return results


# Convert words to Token-derived types according to the given options,
# raising an exception for non-matching words.
# TODO this wants the options to be provided in the order they were declared
def tokenize_options(words, options):
    # Make a mutable copy for local use: matching token objects will get
    # nailed down in-place.
    options = list(options)
    # Tokenized versions of matching words.
    tokens = [None] * len(words)

    w = 0
    while w < len(words):
        matched = match_words(words[w:], options)
        tokens[:len(matched)] = matched
        if matched:
            # Skip past any matched words.
            w += len(matched)
        else:
            w += 1

    if None in tokens:
        # Something didn't get tokenized.
        raise Exception(CLI_ERR_BADOPTION_ARG % words[tokens.index(None)])

    return tokens


def find_token_option(token, options):
    '''Find which option a (nailed) token came from.'''
    for opt in options:
        if token.parent in opt.args:
            return opt


def check_required_options(tokens, options):
    '''Make sure all required options were filled in.'''
    filled_opts = []
    for token in tokens:
        filled_opts.append(find_token_option(token, options))

    for opt in options:
        if opt.required and opt not in filled_opts:
            raise Exception(CLI_ERR_OPT_REQD)


def help_options(cmdobj, words):
    '''
    Returns a list of strings that can be entered according to the list of
    (Option class-derived) options, without any that are in words. The strings
    are typically derived from Str_help i.e. have a help_text attribute.
    '''
    results = []
    for opt in cmdobj.options:
        tokens = opt.next_token(words[len(cmdobj.command):])
        if not tokens:
            continue
        if tokens[-1] is None:
            # Tokens before None are the *only* ones that can follow.
            results = []
            for token in tokens[:-1]:
                results.extend(token.syntax())
            break
        else:
            for token in tokens:
                results.extend(token.syntax())

    return results


# match() method in subclasses returns [matching-tokens]
class Option(object):
    def __init__(self, *args, **kwargs):
        self.required = kwargs.get('required', False)
        self.args = []
        for arg in args:
            if isinstance(arg, str) or isinstance(arg, tuple):
                # Convert bare strings or Str_help tuples to TKeyword object.
                self.args.append(TKeyword(arg))
            else:
                # Already a Token-derived object.
                self.args.append(arg)

    def __repr__(self):
        return "<%s>" % (self.__class__.__name__)

    def complete(self, tokens, words):
        results = []
        for token in tokens:
            if words[-1] == '':
                # More an enumeration than a completion.
                results.append(token.enum())
                continue
            else:
                results.extend(token.complete(words[-1]))
        return results


class Opt_one(Option):
    '''Match at most one of the tokens.'''
    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)

    # In order to successfully match, one word must match one of the
    # option's arguments; if more than one word matches it's an error.
    def match(self, words):
        matches = []
        for w in range(len(words)):
            for token in self.args:
                if not token.verify(words[w]):
                    continue
                matches.append(token.nailedcopy(words[w]))

        if len(matches) > 1:
            raise EOptionMismatch(CLI_ERR_SUPERFLUOUS)

        return matches

    def next_token(self, words):
        for arg in self.args:
            for word in words:
                if arg.verify(word):
                    # Got a match, and only one is allowed.
                    return []
        # None matched so far, any one will do then.
        return self.args


class Opt_any(Option):
    '''Any (or none) of the tokens can be provided, in any order.'''
    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)

    # TODO buggy
    def match(self, words):
        matches = []
        for w in range(len(words)):
            for token in self.args:
                if not token.verify(words[w]):
                    continue
                matches.append(token.nailedcopy(words[w]))
            # Stop after the first unsuccessful match.
            if w + 1 != len(matches):
                break

        return matches

    def next_token(self, words):
        matches = self.match(words[1:])
        tokens = list(self.args)
        for match in matches:
            tokens.remove(match.parent)

        return tokens


class Opt_any_order(Option):
    '''Any (or none) of the tokens can be provided, in the specified order.
    Matching must start with the first word and token.'''
    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)

    def match(self, words):
        matches = []
        args = list(self.args)
        for w in range(len(words)):
            for token in args:
                if token.verify(words[w]):
                    matches.append(token.nailedcopy(words[w]))
                    args.pop(0)
                    break
                else:
                    # Stop after the first unsuccessful match.
                    return matches

        return matches

    def next_token(self, words):
        results = []
        matches = self.match(words)
        if len(matches) < len(self.args):
            results.append(self.args[len(matches)])
        return results


# TODO
class Opt_all(Option):
    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)


class Opt_all_order(Option):
    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)

    def match(self, words):
        a = 0
        matches = []
        for w in range(len(words)):
            if not self.args[a].verify(words[w]):
                return []
            matches.append(self.args[a])
            a += 1
            if a == len(self.args):
                break

        if len(matches) < len(self.args):
            raise EOptionMismatch(CLI_ERR_OPT_REQD)
        elif len(matches) > len(self.args):
            raise EOptionMismatch(CLI_ERR_SUPERFLUOUS)

        w = 0
        tokens = []
        for m_token in matches:
            tokens.append(m_token.nailedcopy(words[w]))
            w += 1

        return tokens

    def next_token(self, words):
        # All option arguments must be supplied in order, so if none of the
        # words match the first argument, that's the only argument that can
        # follow.
        if not words:
            return [self.args[0]]

        for w in range(len(words)):
            if self.args[0].verify(words[w]):
                break
        if w == len(words):
            # No match found.
            return [self.args[0]]

        # Found word matching the first argument. Step through the given
        # words until we find where in the arg list they end, so we
        # can return the next available word.
        a = 0
        while w < len(words):
            if self.args[a].verify(words[w]):
                # This argument has been used.
                a += 1
                w += 1
                if a == len(self.args):
                    # No more arguments.
                    return []
                elif w == len(words):
                    # No more words, so the next argument is the only thing
                    # that can follow. No other options need apply.
                    return [self.args[a], None]
            else:
                return [self.args[a]]

        return []

    def complete(self, tokens, words):
        results = []
        for token in tokens:
            results.extend(token.complete(words[-1]))

        return results


# Some basic tests of the implemented options, hopefully testing all cases.
# This should be moved into a test framework for the whole CLI.
if __name__ == '__main__':
    from tokens import TKeyword, TInteger
    tests = (
        (
            Opt_one,
            (TKeyword('foo'), TInteger(), TKeyword('bar')),
            (
                ('single word matching', [0], ('foo',)),
                ('single word not matching', [], ('baz',)),
                ('first of two matches', [0], ('12', 'baz')),
                ('second of two matches', [1], ('baz', 'foo')),
                ('two matches', [], ('foo', 'bar')),
            ),
        ),
        (
            Opt_any_order,
            (TKeyword('foo'), TKeyword('bar'), TKeyword('baz')),
            (
                ('full match', [0, 1, 2], ('foo', 'bar', 'baz')),
                ('no match', [], ('one', 'two',)),
                ('partial match', [0, 1], ('foo', 'bar')),
                ('partial not first', [], ('bar', 'baz')),
                ('partial non-sequential', [0], ('foo', 'baz')),
                ('full out of order', [], ('baz', 'foo', 'bar')),
                ('partially out of order', [], ('baz', 'bar', 'foo')),
            ),
        ),
    )
    for option_type, option_args, cases in tests:
        title = False
        test = option_type(*option_args)
        for case in cases:
            expected = []
            for i in case[1]:
                expected.append(test.args[i])
            try:
                matches = test.match(case[2])
            except EOptionMismatch:
                matches = []
            result = []
            for m in range(len(matches)):
                result.append(matches[m].parent)
            if result != expected:
                if not title:
                    print "Test %s%s" % (test, option_args)
                    title = True
                print "    Failed %s: %s got %s instead of %s" % (
                        case[0], case[2], result, expected)
