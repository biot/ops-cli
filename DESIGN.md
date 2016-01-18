General design principles
=========================
* Implementation a new command should be easy, so that people can contribute
    new commands with as little scope for error as possible.

* It is important that command modules are easy to read, understand and debug.
    To that end, avoid Python expressions that reverse the normal flow of a
    program, or use a concise syntax at the expense of readability. In
    particular avoid lambdas, list comprehensions, `X if Y else Z`
    expressions, and the like.

* The CLI dispatcher should do as much of the work as it can, including
    all parsing, organizing all the command’s arguments into tokens of
    the appropriate type, and validating them.

    The  command module should not do any syntax validation when that
    syntax can be expressed through a combination of token and option types.

* Command modules should do no infrastructure error checking; for example
    a failure to grab a certain value from OVSDB should raise an exception
    in another (non-CLI) layer, which will be caught in the CLI dispatcher.
    The dispatcher will show some appropriate error to the user and/or log a
    more complete message to a debug log. Control will never return to the
    command module, so it doesn't have to check for errors.

* No output formatting should be done; a set of formatters for common sets
    (tables, lists, …) is available for command modules to use in the
    opscli.output module. This will also take care of paging.

* There needs to be an intermediate layer between OVSDB and commands;
    command modules should never make OVSDB calls or betray knowledge of
    the database structure.
    However it needs a way to specify information it needs, things it wants
    done, and understand information it gets back.


Commands
========
A command consists of an object derived from the `Command` class, registered
at with the CLI into a command tree.

The command object's docstring serves as the help text for that command. The
object attribute `command` contains a string that describes the base command
string to be typed, without options.

The `options` and `flags` attributes are optional. The `run()` method is invoked
when the command is typed, with two arguments:

* `opts` contains a list of tokens corresponding to the options specified by
    the user, according to the various syntax constrainst expressed in the
    command's `options` attribute. The `run()` method is guaranteed not to be
    invoked unless the syntax constraints are satisfied.

* `flags` contains a list of flags appropriate to the invocation.


Options
=======
A command module can declare optional arguments by adding an `options`
variable. If present, this should contain a tuple with one or more option
stanzas; that is, objects derived from the Option base class.

Each option contains a set of possible tokens that may occur in that stanza.
A token may be either a string denoting a keyword, or an object derived from
the Option base class.

The following methods **must** be implemented in Option-derived objects:

* `match(words)` Returns a list of nailed tokens which match the respective
    given words, according to the option type's constraints.

* `next_token(words)` Returns a list of tokens that can be given in this
    option, considering the `words` provided. If no token is appropriate,
    for example because all available tokens have been provided in `words`,
    this returns an empty list.

    If the list of tokens returned are the **only** tokens that apply,
    the last item in the list in `None`. In that case, any other options'
    token lists are discarded.

* `complete(word)` Returns a list of words that start with `word`.


Option types
------------
The following Option types are defined:

* `Opt_one()` At most one of the tokens may be used, if any. When `required`
    is set in this option, exactly one of the tokens is required.

* `Opt_any()` Any (or none) of the tokens can be provided, in any order.
    When `required` is set in this option, exactly one of the tokens is
    required.

* `Opt_any_order()` Any (or none) of the tokens can be provided, in the order
    provided. Matching must start with the first word and token.

* `Opt_all()` If any of the tokens are provided, they must all be provided,
    in any order. When `required` is set in this option, all tokens must
    be provided.

* `Opt_all_order()` Like `Opt_all()`, but any tokens provided must be in
    the same order as they are declared.

    For example, `OAllOrder('maxsize', TInteger())` means that if 'maxsize'
    is used, it must be followed by an integer argument.


Tokens
======
Tokens are objects derived from the Token base class. The following class
variables may be declared:

* `decription` Capitalized description.

Token objects implement the following methods:
* `nail(word)` Called by the CLI dispatcher when it determines this token
    type will be used for the word entered by the user. This calls the
    `verify()` method if available, and raises ValueError if that fails.
    After this method has been called the object has a `value` attribute
    available corresponding to the nailed and verified value of word,
    cast to the appropriate Python type. Practically speaking this is
    an integer for the TInteger token type, and a string for all others.
* `enum()` Returns a list of all possible values. For example, the TInterface
    token object returns a list of interfaces on the system.
* `complete(word)` Returns a list of words that start with `word`.
* `syntax()` Returns the canonical syntax for this token. It is a list of
    possible words for this token. In some cases, such as TInterface, this
    is a string like `<interface>`. The list items are Str_help instances,
    including any help text declared in the command module.
* `verify(word)` Verify whether `word` is a valid name for this token type,
    returning True or False.. This can be called without affecting the
    object (i.e. the verified value is not stored), but is also called
    automatically when `nail()` is invoked.

A Token object is instantiated when a command module is loaded which declares
it, with the arguments provided for that particular instance. When the CLI
dispatcher decides to match a word entered by the user to that instance, its
`nail()` method is called.

Token help text
---------------
All strings used as tokens can be specified either as regular `strings`, or
as two-element tuples. In this case the first element is the string, and the
second is help text related to that string.

For example, the `logrotate` command's `period` keyword takes a string
argument. It can be declared like this:

```
Opt_all_order(
    'period',
    TString('hourly', 'weekly', 'monthly')
)
```
All of these strings can have help text attached, like this:
```
Opt_all_order(
    ('period', 'Rotation period'),
    TString(
        ('hourly', 'Rotate log files every hour'),
        ('weekly', 'Rotate log files every week'),
        ('monthly', 'Rotate log files every month'),
    ),
)
```

Non-string tokens, such as TInteger, can have help text attached with a
`help_text` keyword argument:
```
Opt_all_order(
    ('maxsize', 'Maximum file size for rotation'),
    TInteger(min_int=1, max_int=200, help_text="File size in MiB"),
),
```


Token types
-----------
These are the defined token types:

* `TString(*args)`
  A simple string. If arguments are provided, the string can only be one of
those arguments. When passed in to the `run()` method, the string actually
passed in is available as the `word` attribute in this object.

  Use of this type without arguments should be avoided, as it will match any
  string; it might thus interfere with the parsing of other options.


* `TKeyword`
  A keyword string. This need not be declared directly in an options
  list; the CLI dispatcher converts regular strings to this type automatically.
  Like TString, the actual keyword passed in is available as `word`.


* `TInteger(min_int=None, max_int=None)`
  An integer, optionally bounded by `min_int` and `max_int`. The integer
  passed in at `run()` is available in the `value` field.


* `TInterface`
  This represents an interface. Only valid interfaces are accepted.
  Like TString, the actual interface passed in is available as `word`.


In addition to these, all token types take the following optional arguments:

* `required=False`
    If True, this token **must** be present in the option. However that does
    not mean the option stanza itself is required (see below).


Flags
=====
Command flags can be specified in the `flags` attribute`, and can be listed in
the `flags` argument to the command's `run()` method. The following flags are
defined:

* `F_NO`
    When specified in the command flags, this indicates that the command can be
    prefixed by `no `, such as in `no shutdown`. If the user does use the "no"
    prefix, the F_NO flag is in the `run()` method's flags argument. The code
    in that method must then check for this flag to  determine if the user wants
    to negate the command.

    If the user specifies "no" before a command that doesn't declare this flag,
    it's a syntax error and the `run()` method will not be invoked.

* `F_NO_OPTS_OK`
    When specified in the command flags, this indicates the command may be
    invoked without any options i.e. only the bare command string. Otherwise,
    a command that declares options need to have at least one specified.

    Note that a command with no declared options doesn't need this flag.


Contexts
========
A command object must be registered with the command shell by calling the
`register_commands()` function. This takes a tuple of command objects as its
first argument, and the name of the context to register the command in as the
optional second argument. If not specified, the default context is 'root'.

The context is a freeform string, used only when registering a command and
jumping into a context. The shell starts in the default ('root') context.

To jump into a new context, call `context_push(context, obj)`. The first
argument is the context. The second argument is a context-specific Python
object significant only to the code using that context. For example, an
interface context might use that object to store a `TInterface` token,
interface name, or even an OVSDB UUID relevant to that interface.

The context-specific object is available to code in the `run()` method of
commands registered in that context by calling the `context_get()` method.
It is automatically discarded when the user exits that context.


