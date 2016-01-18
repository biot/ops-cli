Adding new commands
===================

The basics
----------

Adding a new command to the shell is easy! The command declaration lets you
specify the command's options and help text, and the shell takes care of
enforcing syntax.

The `ops-cli` program is a small script that takes a few arguments:

* **-s server**

  An OVSDB server string, such as `tcp:172.0.7.1:6640`


* **-d debug-options**

  Comma-separated list of debug facilities to turn on


It contains a list of directories in which to find command modules. This is
currently just the `cli-commands` directory in the same directory as this
script.

Every command module is a Python program, i.e. must have a `.py` suffix.
Only files that starts with `cli_` are loaded as modules, so you can have
custom Python files in that directory that aren't picked up by the command
module loader.

A command is a class definition with a parent class `Command`, as defined
in `opscli.command`. A command module can have any number of these defined.

The module must also register its commands into the command tree, by calling
the `register_commands()` function with a tuple listing the commands.

Here's a bare-bones command module:

```python
from opscli.command import *
from opscli.output import *

class Show_version(Command):
    '''Version information'''
    command = 'show version'

    def run(self, opts, flags):
        cli_out('Version 0.1')


register_commands((Show_version,))
```

The [docstring](https://www.python.org/dev/peps/pep-0257/) under the class
definition is what the user sees as help for the command, for example:

```
switch> show ver?
  show            Version information
switch> show ver
```

The `command` string defines the actual command the user types to get to
this command.

The `run` method is the only method that must exist. It's run when the user
invokes the command (or a shortened, non-ambiguous version of it).
`opts` contains a list of options the user added after the command. No
options were defined for the command above, so this will be empty.
`flags` is a list of flags that apply.

Let's add some options to the command:

```python
from opscli.command import *
from opscli.output import *

class Show_version(Command):
    '''Version information'''
    command = 'show version'
    options = (
        Opt_one('hardware', 'software'),
    )

    def run(self, opts, flags):
        if 'hardware' in opts:
            cli_out('Hardware version 0.1')
        if 'software' in opts:
            cli_out('Software version 0.1')


register_commands((Show_version,))
```

Those options are available from the built-in help system:

```
switch> show ver ?
  hardware             
  software             
switch> show ver
```

But there's no help text, just the options. Let's fix that by adding
some help text:

```python
command = 'show version'
options = (
    Opt_one(
        ('hardware', 'Hardware information'),
        ('software', 'Software information'),
    ),
)
```

That's all you need for inline help:

```
switch> show ver ?
  hardware             Hardware information
  software             Software information
switch> show ver hardware
Hardware version 0.1
switch> 
```

The option keywords above were enclosed in `Opt_one`. That's an option
grouping where only one of the option arguments can be specified, but no
more:

```
switch> show ver hardware software
% Superfluous option.
switch> 
```

Note that the error message was supplied by the shell; the command's
`run()` method was not invoked. By using `Opt_one()`, the shell can
enforce the option syntax.

The code above is still a little sloppy: if you invoke it without specifying
the `hardware` or `software` options, it just doesn't output anything. Let's
make it so at least one of them always has to be given:

```python
command = 'show version'
options = (
    Opt_one(
        ('hardware', 'Hardware information'),
        ('software', 'Software information'),
        required=True,
    ),
)
```

This makes it a required option:

```
switch> show ver 
% Required option missing.
switch> 
```

This also means the code in the `run()` method never has to check for
syntax errors: it is guaranteed to be called **only** when exactly one of
those two keyword was specified.


A few more tokens
----------------

The options in the example above are all keywords. These look like strings,
and are used as such in the `run()` method, but they're actually tokens.
A token is an object derived from the `Token` class. In the case above,
they are TKeyword objects.

Here's an example of an option that uses a TInteger object:

```python
from opscli.tokens import TInteger

class Set_protocol_version(Command):
    '''Set protocol version'''
    command = 'set protocol'
    options = (
        Opt_one(
            TInteger(min_int=1, max_int=5),
            required=True,
        ),
    )

    def run(self, opts, flags):
        cli_out("Setting protocol version %s" % opts[0])
```

The `TInteger()` declaration guarantees only an integer can be specified,
and the `min_int` and `max_int` arguments restrict it to an integer between
1 and 5. These are optional: when not specified, it only has to be a valid
integer.

Since the option has `required=True`, the code can use `opts[0]` to
get the specified integer without checking: it will only ever run if there
is exactly one option in there.

What's missing here is help text though:

```
switch> set proto ?
  1-5
switch> set proto 
```

When using tokens that don't take strings, you can always specify help
text like this:

```python
options = (
    Opt_one(
        TInteger(min_int=1, max_int=5, help_text='Version to set'),
        required=True),
)
```

That works as expected:

```
switch> set proto 
  1-5                  Version to set
switch> set proto 
```

There's one more thing missing. Let's say this is the first `set` command
we're adding, so `set protocol` created a branch in the command tree for
`set`, then one for `protocol` under that. But now the `set` command has
no help text:

```
switch> set ?
  set                  No help provided.
switch> set
```

Let's add a little dummy command, just so we can get some help text in there:

```python
class Set(Command):
    '''Set various things'''
    command = 'set'
```

We don't even need a `run()` method here:

```
switch> set ?
  set                  Set various things
switch> set
```

Don't forget to add dummy commands to your `register_commands()` call!

Let's take a look at one more token type: strings. These are a set of strings
the user can specify:

```python
class Logrotate(Command):
    '''Configure log rotation policy'''
    command = 'logrotate'
    options = (
        Opt_all_order(
            'period',
            TString('hourly', 'weekly', 'monthly'),
        ),
    )
```

The syntax for this command is for example

```
switch> logrotate period weekly
```

We're using another option type here, `Opt_all_order`. This means that if
any of this option's arguments is specified, they **must** all be specified,
in the order declared. That's a good way to specify that if `period` is
specified, it must be followed by `hourly`, `weekly`, or `monthly`.

The `TString` token just takes a list of strings. But notice we're missing
help text for these options again. Since these are all declared as strings,
we can just make them tuples in the form

```
('string', 'help text')
```

The result looks like this:

```python
class Logrotate(Command):
    '''Configure log rotation policy'''
    command = 'logrotate'
    options = (
        Opt_all_order(
            ('period', 'Rotation period'),
            TString(
                ('hourly', 'Rotate log files every hour'),
                ('weekly', 'Rotate log files every week'),
                ('monthly', 'Rotate log files every month'),
            ),
        ),
    )
```

Here's the help text in action:

```
switch> logrotate ?
  period               Rotation period
switch> logrotate period ?
  hourly               Rotate log files every hour
  weekly               Rotate log files every week
  monthly              Rotate log files every month
switch> logrotate period 
```


Summary
-------

* Command modules have to start with `cli_` and end with `.py`.
* Commands are classes derived from the Command class, and must be registered
  with a call to `register_commands()`.
* The `run()` method is invoked only with a correct syntax, as defined
  by the command string and options.
* You can structure options by choosing their type: `Opt_one` allows
  only one to be used, `Opt_all_order` needs all of them,  in order.
  Adding `required=True` makes the option mandatory.
* Options consist of tokens; bare strings are actually TKeyword tokens,
  but you can also use `TInteger` and `TString` tokens.
* A full list of option and token types is in the [design document](DESIGN.md).

