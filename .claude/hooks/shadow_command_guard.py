#!/usr/bin/env python3
"""Refuse the construction of a stub command that shadows a real one.

CE-2.19. "Never build test infrastructure unasked" is a HARD BLOCK in the
shared rules and was, until this file, the only one with nothing behind it. On
2026-09-11 it was broken three times in one evening, by me, while working on
the enforcement machinery itself. Patrick: *"It's just the same shit, over and
over and over. It doesn't matter what I do to try to stop you."*

WHAT THIS REFUSES, AND WHY IT IS THAT AND NOT "A TEST RIG"

    "Is this a test harness" has no mechanical answer. "Is this a file that
    will be found INSTEAD of a real command" does, and it is the move every rig
    that evening actually made:

        printf '#!/bin/sh\\n...' > $S/bin/claude ; chmod +x $S/bin/claude
        PATH=$S/bin:$PATH  glm-agent qa ...

    A stub named `claude`, first on PATH, so the runner launches it instead of
    the real binary. Both rigs did exactly that -- the one I wrote and the one
    I instructed a Clyde to build.

    Shadowing is also the family the orphan guard was bounced on twice:
    `./kill` runs a FILE rather than the builtin, and a bash function named
    `kill` runs instead of either. A name does not say what it resolves to.
    This hook refuses the act of arranging that.

THE DISCRIMINATOR

    Creating a file named after a real command is not by itself wrong -- the
    repo legitimately contains `bin/glm-agent`, and `glm-agent` resolves on
    PATH. Two things separate a shadow from the real thing:

      * it is written OUTSIDE any git work tree -- scratch, /tmp. The real
        copies of these commands live in repos; a rig deliberately does not.
      * or the same command prepends its directory to PATH.

    Editing the real file in its own repo trips neither.

WHAT IT DOES NOT REACH, STATED RATHER THAN IMPLIED

    A dispatch prompt that instructs ANOTHER agent to build the rig. The Agent
    tool carries its prompt in the payload and could be scanned, but the way
    these are actually dispatched is `glm-agent qa opus --ticket X "$(cat
    file)"` -- the instruction lives in a file the shell expands, so the hook
    sees `$(cat file)` and nothing more. Scanning the visible text would catch
    the spelling nobody uses while missing the one everybody uses, and would
    fire on any prompt that merely DISCUSSES PATH, including the one reporting
    this gap.

    So that half is not covered. CE-2.19's AC3 asks for exactly this to be
    recorded rather than half-built, and it is recorded here. The surface is
    the one the QA brief had to be protected from by having the runner attach
    it: what one agent writes for another is unguarded, and a content scan is
    not the answer.

Input: PreToolUse JSON on stdin. Blocks with exit 2, allows with 0.
"""

import glob
import json
import os
import re
import shlex
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    CODE_INTERPRETERS, GIT_GLOBAL_FLAGS_WITH_VALUE, QUOTED, SHELLS,
    expand_assignments, payload_of, statements, strip_heredoc_bodies,
    strip_wrappers, target_directory)

BLOCK = 2
ALLOW = 0

# `d=/tmp/x` then `PATH=$d:$PATH` is the same move split across statements, so
# the prepend is matched against the whole command rather than per statement.
PATH_PREPEND = re.compile(r'\bPATH\s*=\s*(?!\$PATH\b)[^\s;|&]*[:$]')

REDIRECT = re.compile(r'>\|?\s*([^\s;|&<>]+)')
# Every spelling of "put a file here". The list was cp/mv/ln/install/tee, and
# the founding rig of fixture 01 walked straight through it by swapping `cp`
# for `rsync` -- same stub, same PATH prepend, allowed (CE-2.19 QA round 1).
# `dd` names its destination with `of=` rather than by position, and `git
# checkout <path>` writes a file without being a copier at all.
COPIERS = ("cp", "mv", "ln", "install", "tee", "rsync")

# The thing that RUNS tests, by the names it actually ships under. A driver is
# recognised by name because that is what it is -- `_invoke.sh` is not a
# fixture that happens to be shell, it is the file the runner delegates to.
DRIVER_NAMES = re.compile(
    r'^(?:_invoke\.sh'
    r'|_[a-z0-9_]+_driver\.sh'
    r'|run-[a-z0-9-]*tests?\.sh'
    r'|conftest\.py'
    r'|pytest\.ini|tox\.ini'
    r'|jest\.config\.[a-z]+'
    r'|vitest\.config\.[a-z]+'
    r'|karma\.conf\.js'
    r'|playwright\.config\.[a-z]+)$'
)

# A tests root, matched at a path boundary so `latest/` is not a test dir.
TEST_ROOT = re.compile(r'(?:^|/)(?:tests?|__tests__|spec)(?:/|$)')

# Shell builtins a definition can shadow. `shutil.which` cannot see these --
# `cd` is not a file anywhere on this machine -- so the which() test alone
# misses the exact spelling used to route around cwd_drift_guard on
# 2026-09-11. Unlike installed binaries, this set is fixed by the shell rather
# than by the machine, so naming them is not the drifting list the docstring
# warns about.
BUILTINS = frozenset({
    "cd", "alias", "unalias", "eval", "exec", "export", "set", "unset",
    "source", "trap", "read", "shift", "command", "builtin", "type",
    "hash", "pushd", "popd", "dirs", "kill", "wait", "jobs", "umask",
})

# `name() {`, `function name {`, `function name() {`
#
# The separator class carries a newline and an open paren because both are
# command positions and both were missing: `set -e\ncd() { :; }` and
# `echo $(cd() { :; })` were ALLOWED while `true; cd() { :; }` was refused --
# the same definition, differing only in the character in front of it, and a
# multiline command is the normal shape here (CE-2.19 QA round 1).
FUNCTION_DEF = re.compile(
    r'(?:^|[;&|{(\n]\s*|\bthen\s+|\bdo\s+|\belse\s+)\s*'
    r'(?:function\s+([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\(\s*\))?\s*\{'
    r'|([A-Za-z_][A-Za-z0-9_-]*)\s*\(\s*\)\s*\{)'
)
ALIAS_DEF = re.compile(
    r'(?:^|[;&|{(\n]\s*|\bthen\s+|\bdo\s+|\belse\s+)\s*'
    r'alias\s+([A-Za-z_][A-Za-z0-9_-]*)\s*=')

# The directory a command puts FIRST on PATH. Populating a directory you are
# also prepending is the shadow move whatever tool does the populating --
# cp, curl, tar, git clone -- so the directory is the thing to watch rather
# than an ever-growing list of ways to put a file in one.
PATH_DIRS = re.compile(r'\bPATH\s*=\s*([^\s;|&]*?):\$?\{?PATH')

# Where a fetcher puts what it downloads, and where an extractor unpacks.
FETCH_DEST = {"curl": ("-o", "--output"),
              "wget": ("-O", "--output-document")}
EXTRACT_DEST = {"tar": ("-C", "--directory"), "unzip": ("-d",)}
GIT_WRITES = ("checkout", "restore")

# `test` and `time` resolve on PATH, so which() calls them real -- but a local
# `test()` helper is how people write shell, not an escape hatch, and refusing
# it was part of finding 6's false-positive class.
IDIOMATIC_LOCALS = frozenset({"test", "time"})


def shadowed(path, base, runnable):
    """The real command `path` would be found instead of, or None.

    `shutil.which` rather than a hardcoded list: which commands are real is a
    property of the machine, and a list here would be one more thing to drift
    out of date. A path that IS where the command already lives is the real
    file being edited, not a shadow of it.

    `runnable` is the discriminator, and its absence was the defect. A shadow
    is a file that will be EXECUTED instead of the real command. A file of the
    same name that nothing can run is not a shadow of anything -- but this
    refused every one of them, and the scratchpad lives outside any work tree
    by the harness's own instruction, so the work-tree escape never applied.
    Redirecting ordinary output into a scratch file called `env`, `diff`,
    `stat`, `sort` or `id` was a wall with no bypass (Grace, finding 6).

    Requiring runnability TIGHTENS the true positive rather than weakening it:
    the founding rig in the docstring above writes a shebang and chmods, and
    is still caught by both halves.
    """
    name = os.path.basename(path.strip().strip('"').strip("'"))
    if not name or name.startswith("."):
        return None
    if not runnable:
        return None
    real = shutil.which(name)
    if not real:
        return None
    try:
        if os.path.realpath(real) == os.path.realpath(resolve(path, base)):
            return None
    except OSError:
        pass
    return name


def in_a_work_tree(path, base):
    """True when `path` sits inside a git work tree.

    Not a judgement about quality. It is the cheap, honest separator between a
    file that belongs to a project and one written to scratch in order to be
    found first. Walked upward rather than shelling out to git, because this
    runs on every Write.
    """
    here = os.path.dirname(resolve(path, base))
    while True:
        if os.path.exists(os.path.join(here, ".git")):
            return True
        parent = os.path.dirname(here)
        if parent == here:
            return False
        here = parent


def _destinations(argv0, operands, base):
    """Where this copier puts things.

    Two shapes, because both were used to walk around the positional read:
    a named destination (`cp src dst`), and a destination DIRECTORY that the
    sources land inside (`ln -s .../_invoke.sh <tests>/`), which creates a
    path no token in the command spells out.
    """
    if argv0 == "dd":
        return [t.split("=", 1)[1] for t in operands if t.startswith("of=")]
    if len(operands) < 2:
        return []
    target, sources = operands[-1], operands[:-1]
    if os.path.isdir(resolve(target, base)):
        return [os.path.join(target, os.path.basename(s)) for s in sources]
    return [target]


SHEBANG = re.compile(r'#!\s*/')


# Anything that moves the shell, in any spelling. This is a DETECTOR, not a
# resolver -- the round-4 fix tried to resolve the cwd itself with a regex
# that recognised only `cd` at a statement boundary, and thereby replaced
# target_directory's answer with one that knew less. target_directory's own
# docstring already knows that pushd moves the shell exactly as cd does, and
# it tracks subshell depth. Overriding it was the defect (CE-13.4 QA round 5,
# which found six spellings it missed: pushd, a subshell cd, `\cd`,
# `cd $(echo S)`, a cd inside `if`, and a brace group).
MOVES_THE_SHELL = re.compile(r'(?:^|[;&|(){}\n]|\bthen\b|\bdo\b|&&|\|\|)'
                             r'\s*\\?(?:cd|pushd)\s+([^\s;&|<>()]+)')


def _cwd_is_uncertain(command, base):
    """True when the shell moves somewhere this cannot pin down.

    Ask the question the resolver's own failure asks. target_directory
    resolves a `cd` against the DISK and silently declines when the target is
    not there, falling back to the directory it already held -- so every mark
    after that point lands somewhere the file will not be. The condition that
    matters is therefore exactly this: DOES A MOVE NAME A DIRECTORY THAT DOES
    NOT EXIST AT SCAN TIME.

    That is the fifth shape of one detector and the first that does not
    enumerate anything. Rounds 1 through 4 chased creators -- install, then a
    staged rename, then cd-relative staging, then a mkdir the resolver could
    not see -- and round 5 replaced the resolver with a regex that knew less.
    Round 6 then broke the creator list eleven ways (CE-13.4 QA): `if mkdir`,
    `for ... do mkdir`, `! mkdir`, `command mkdir`, `sudo mkdir`, `until
    mkdir`, `install -d` behind `if`, a variable holding the mkdir, and --
    the ones that end the argument -- `git clone` and `tar xf`, which make a
    directory without a creator token anywhere in the command.

    Enumerating creators could never close, because ANYTHING can make a
    directory. The directory's absence is the same fact seen from the side
    that is finite: there is one of it, and it is the fact the resolver
    actually trips over. A move into a directory that does exist resolves
    correctly and needs no special case, which is also why this is NARROWER
    than the mkdir test it replaces -- `mkdir -p new && cd /somewhere/real`
    no longer trips anything.

    An unreadable target -- a variable, a substitution, a quoted path this
    cannot split -- does not resolve either, and is treated the same way.

    The cost is unchanged and is the direction this guard calls recoverable:
    a command that moves into a fresh directory AND names its output after a
    real command is refused.
    """
    prefix = []
    for statement in statements(strip_heredoc_bodies(command or "", False)):
        # The base for THIS statement's move is wherever the moves before it
        # left the shell, which is the resolver's job, not this function's.
        here = target_directory(" && ".join(prefix), default=base)
        prefix.append(statement)
        for target in MOVES_THE_SHELL.findall(statement):
            path = os.path.expanduser(target)
            if not os.path.isabs(path):
                path = os.path.join(here, path)
            if not os.path.isdir(os.path.normpath(path)):
                return True
    return False


def _destinations_of(statement, here):
    """Every path this one statement writes, whatever tool it uses."""
    try:
        tokens = shlex.split(statement)
    except ValueError:
        return []
    argv, _ = strip_wrappers(tokens)
    if not argv:
        return []
    argv0 = os.path.basename(argv[0])
    operands = [x for x in argv[1:] if not x.startswith("-")]
    out = list(REDIRECT.findall(statement))
    if argv0 in COPIERS or argv0 == "dd":
        out += _destinations(argv0, operands, here)
    return out


def runnable_targets(command, base):
    """Paths this command would leave EXECUTABLE.

    Three ways, per Grace's finding 6: the command chmods the path executable,
    it writes a shebang into it, or it copies something that is already
    executable. Anything else is a data file that happens to share a name with
    a command, and refusing those was a wall with no bypass.

    The shebang test is deliberately coarse -- a shebang anywhere in the
    command marks that command's redirect targets. Erring toward calling a
    file runnable errs toward refusing, which is the safe direction here.
    """
    out = set()
    prefix = []
    uncertain = _cwd_is_uncertain(command, base)

    def mark(paths, here):
        out.update(resolve(p, here) for p in paths)

    for statement in statements(strip_heredoc_bodies(command, False)):
        # The directory in effect AT this statement, not one base for the
        # whole command. `cd a && install x` then `cd b && mv x y` resolved
        # the staging path and the move source against different directories,
        # so the mark never matched and the rename escaped -- the third
        # generation of this defect (CE-13.4 QA round 3). The single-cd
        # spelling worked, which is what made it look fixed.
        prefix.append(statement)
        here = target_directory(" && ".join(prefix), default=base)
        # target_directory resolves against the DISK, so a cd into a
        # directory this same command just made returns nothing and every
        # mark lands at the session base instead. `mkdir -p S && cd S &&
        # install x && cd elsewhere && mv S/x env` therefore escaped: the
        # install mark went to the wrong place, the mv source never matched
        # (CE-13.4 QA round 4, the fourth generation of one mistake).
        #
        # The mkdir is already visible in the prefix, so honour it rather
        # than asking the filesystem.
        if uncertain:
            # The shell moves into a directory this command is creating, so
            # no resolution here is trustworthy. Everything written is
            # treated as runnable and shadowed() decides on the NAME.
            mark(_destinations_of(statement, here), here)
        # Per statement, IN ORDER, because runnability propagates. A file made
        # executable under a harmless staging name and then moved onto a
        # command name is the same rig in two steps, and tracking paths rather
        # than dataflow missed it: the destination's source does not exist at
        # scan time, so nothing marked it. `install /bin/true /tmp/x/pwn && mv
        # /tmp/x/pwn ~/.local/bin/env` was refused before the finding-6 change
        # and allowed after (CE-13.4 QA round 2, verified by QA on the real
        # system -- install leaves 755, mv preserves it, the result executes,
        # and ~/.local/bin is PATH entry 1).
        if SHEBANG.search(statement):
            mark(REDIRECT.findall(statement), here)
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        argv, _ = strip_wrappers(tokens)
        if not argv:
            continue
        argv0 = os.path.basename(argv[0])
        operands = [x for x in argv[1:] if not x.startswith("-")]
        if argv0 == "chmod" and len(operands) > 1:
            mode = operands[0]
            if "x" in mode or re.search(r'[1357]', mode):
                mark(operands[1:], here)
        elif argv0 == "install":
            # `install` makes its DESTINATION executable -- GNU's default
            # mode is 0755 -- so modelling runnability on the source's exec
            # bit missed it entirely. `install payload.sh ~/.local/bin/env`
            # is a complete one-command rig: no chmod token, no shebang
            # token, no PATH prepend for any predicate to see, and
            # ~/.local/bin sits ahead of /usr/bin. Verified by QA on the
            # real system, a 644 source becoming a 755 destination that
            # runs. It is the next token after cp and rsync in the sequence
            # fixture 19 exists to record.
            mode = _flag_value(argv, ("-m", "--mode"))
            if mode is None or "x" in mode or re.search(r'[1357]', mode):
                mark(_destinations(argv0, operands, here), here)
        elif argv0 in COPIERS and len(operands) > 1:
            chmod = _flag_value(argv, ("--chmod",))
            grants_exec = bool(chmod and ("x" in chmod
                                          or re.search(r'[1357]', chmod)))
            sources = operands[:-1]
            # `resolve(s) in out` IS the propagation: a source this same
            # command already made runnable carries that to the destination.
            if grants_exec or any(os.access(resolve(s, here), os.X_OK)
                                  or resolve(s, here) in out
                                  for s in sources):
                mark(_destinations(argv0, operands, here), here)
            if argv0 == "tee":
                # tee writes EVERY operand, not just the last one.
                mark(operands, here)
    return out


def _flag_value(argv, flags):
    """The value of the first of `flags` present in argv, or None."""
    for flag in flags:
        if flag in argv and argv.index(flag) + 1 < len(argv):
            return argv[argv.index(flag) + 1]
        for token in argv:
            if token.startswith(flag + "="):
                return token.split("=", 1)[1]
    return None


def git_subcommand(argv):
    """git's subcommand and its operands, past any GLOBAL flags.

    `git -C <dir> checkout <path>` hid the verb from a read of a fixed
    argument slot, so the checkout was invisible (CE-2.19 QA round 2).
    """
    index = 1
    while index < len(argv):
        token = argv[index]
        if token in GIT_GLOBAL_FLAGS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, [t for t in argv[index + 1:]
                       if not t.startswith("-") and t != "--"]
    return None, []


def _written_in(statement, here):
    """Paths this ONE statement would create, copy to, or make executable,
    resolved against `here`.

    Split out of created_paths so the same per-statement rule can be walked
    either against a single base (created_paths' own callers, unchanged) or
    against the directory actually in effect when THIS statement runs
    (_infra_candidates, below -- CE-2.39).
    """
    found = list(REDIRECT.findall(statement))
    try:
        tokens = shlex.split(statement)
    except ValueError:
        return found
    argv, _ = strip_wrappers(tokens)
    if not argv:
        return found
    argv0 = os.path.basename(argv[0])
    operands = [t for t in argv[1:] if not t.startswith("-")]
    if argv0 in COPIERS or argv0 == "dd":
        found += _destinations(argv0, operands, here)
    if argv0 in FETCH_DEST:
        dest = _flag_value(argv, FETCH_DEST[argv0])
        if dest:
            found.append(dest)
    if argv0 == "git":
        sub, rest = git_subcommand(argv)
        if sub in GIT_WRITES:
            found += rest
    if argv0 == "chmod" and len(operands) > 1:
        found += operands[1:]
    return found


def created_paths(command, base):
    """Paths this command would create, copy to, or make executable.

    Read through shell payloads as well as the command itself: the entire
    founding rig quoted inside `bash -c` was allowed while the same text
    unquoted was refused, because only redefinitions() read payloads
    (CE-2.19 QA round 2).
    """
    found = []
    for text in _shell_texts(command):
        for statement in statements(strip_heredoc_bodies(text, False)):
            found += _written_in(statement, base)
    return found


def redefinitions(command):
    """(kind, name) for every definition that shadows an existing command.

    The docstring above already claims this family -- "a bash function named
    `kill` runs instead of either. A name does not say what it resolves to.
    This hook refuses the act of arranging that" -- and until now claimed it
    without checking it. Every spelling was allowed, including that very
    example.

    It is not a hypothetical. `cd() { :; };` was prefixed onto shell commands
    throughout 2026-09-11 to stay clear of cwd_drift_guard: a hand-built
    escape hatch, of exactly the kind the zero-trust rule forbids, arranged
    through the one shadowing spelling that touches no file and so was
    invisible to a guard that only inspects paths.

    Quoted regions are masked first, so prose or a fixture that merely
    DESCRIBES a definition is not read as making one.
    """
    found = []
    for text in _texts_to_scan(command):
        for match in FUNCTION_DEF.finditer(text):
            name = match.group(1) or match.group(2)
            if name in IDIOMATIC_LOCALS:
                continue
            if name and (name in BUILTINS or shutil.which(name)):
                found.append(("function", name))
        for match in ALIAS_DEF.finditer(text):
            name = match.group(1)
            if name and (name in BUILTINS or shutil.which(name)):
                found.append(("alias", name))
    return found


STRING_LITERAL = re.compile(r"""['"]([^'"\n]{3,})['"]""")


def _literals_in(statement):
    """String literals from a python/ruby/node payload in this ONE statement.

    Split out of _source_literals for the same reason _written_in was split
    out of created_paths: a per-statement extraction that a per-statement
    walk can call (_infra_candidates, below -- CE-2.39).
    """
    try:
        tokens = shlex.split(statement)
    except ValueError:
        return []
    argv, _ = strip_wrappers(tokens)
    if not argv:
        return []
    argv0 = os.path.basename(argv[0])
    if argv0 not in CODE_INTERPRETERS:
        return []
    payload = payload_of(argv0, argv[1:])
    if not payload:
        return []
    return STRING_LITERAL.findall(payload)


def _source_literals(command):
    """Quoted string literals from python/ruby/node payloads.

    Tokenising an interpreter payload is fiction, so this does not try. It
    reads the payload's string literals as candidate paths, the same
    fail-closed treatment the sibling guards give source they cannot parse.
    A `python3 -c` that copies a stub onto PATH, or writes a driver, is
    invisible without it -- QA round 2's primary finding.
    """
    out = []
    for statement in statements(strip_heredoc_bodies(command, True)):
        out += _literals_in(statement)
    return out


def _infra_candidates(command, session):
    """(path, here) for every path new_test_infrastructure must judge.

    created_paths and _source_literals hand every candidate the command's
    FINAL directory, whatever statement actually named it -- correct for a
    command with no `cd`, and wrong for one that has: a path used BEFORE a
    `cd` was being judged against the directory the `cd` moves TO. Fixture
    28 reads a file and only then changes directory, and was refused because
    the read was resolved against where the shell ended up rather than
    where it was when the read actually ran.

    Variables are expanded first, best-effort, the same pass target_directory
    itself is handed for a `cd` elsewhere in this file: a `cd $W` this can
    now follow moves `here` for every statement after it exactly as a
    literal `cd` would, and a redirect target held in a variable resolves to
    what it actually names instead of to the literal, unexpanded text.
    Fixture 29 is that case -- at HEAD the guard cannot follow `cd $W`, so it
    never leaves the session's own directory, and the unexpanded `$S/...`
    reads as a new directory under it (CE-2.39).
    """
    expanded = expand_assignments(command)
    out = []
    for text in _shell_texts(expanded):
        prefix = []
        for statement in statements(strip_heredoc_bodies(text, False)):
            here = target_directory(" && ".join(prefix), default=session)
            prefix.append(statement)
            out += [(p, here) for p in _written_in(statement, here)]
        prefix = []
        for statement in statements(strip_heredoc_bodies(text, True)):
            here = target_directory(" && ".join(prefix), default=session)
            prefix.append(statement)
            out += [(p, here) for p in _literals_in(statement)]
    return out


def _shell_texts(command):
    """The command itself, plus every shell payload it carries.

    redefinitions() read payloads from the start; created_paths and
    directories_created did not, so the whole rig quoted inside `bash -c`
    was allowed while the same text unquoted was refused, and so was a mkdir
    of a new tests root (CE-2.19 QA round 2).
    """
    return [command] + _shell_payloads(command)


def _shell_payloads(command, depth=0):
    """Shell code carried as a quoted ARGUMENT: `eval '..'`, `bash -c '..'`.

    The main scan masks quoted regions so that prose describing a definition
    is not read as making one. That protection also hid every interpreter
    payload, so `bash -c 'cd() { :; }'` was allowed while the same text
    unquoted was refused (CE-2.19 QA round 1). A payload is quoted AND it is
    code, and code gets read -- the same distinction strip_heredoc_bodies
    already draws for heredocs.
    """
    if depth > 4:
        return []
    out = []
    for statement in statements(strip_heredoc_bodies(command, True)):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        argv, _ = strip_wrappers(tokens)
        if not argv:
            continue
        argv0 = os.path.basename(argv[0])
        if argv0 in SHELLS or argv0 == "eval":
            code = payload_of(argv0, argv[1:])
            if code:
                out.append(code)
                out.extend(_shell_payloads(code, depth + 1))
    return out


def _texts_to_scan(command):
    """The command with quotes masked, plus every shell payload, unmasked.

    A heredoc fed to a shell needs no special case: strip_heredoc_bodies keeps
    an interpreter's body inline, so the definition lands in the masked text
    on its own line -- which is why the newline separator above matters.
    """
    kept = strip_heredoc_bodies(command, True)
    yield QUOTED.sub(lambda m: " " * len(m.group()), kept)
    for payload in _shell_payloads(command):
        yield payload


def redefinition_refusal(kind, name):
    return (
        f"\n[shadow_command_guard] BLOCKED: this defines a {kind} named "
        f"`{name}`, which already means something else.\n\n"
        "A name does not say what it resolves to. A shell function or alias\n"
        "named after a real command runs INSTEAD of it, for every later\n"
        "command in that shell -- the same act as putting a stub first on\n"
        "PATH, minus the file.\n\n"
        "This spelling was used on 2026-09-11 to slip past a guard: a no-op\n"
        f"`cd` so a command would not be seen moving the shell. Arranging a\n"
        "name to resolve somewhere else in order to get past a check is an\n"
        "escape hatch, and there are none.\n\n"
        "If a command needs different behaviour, call the different thing by\n"
        "its own name. If a guard is refusing something it should not, say\n"
        "so and leave it refused -- do not arrange for it to stop seeing."
    )


def resolve(path, base):
    """Resolve `path` against the repo the COMMAND is about.

    `os.path.abspath` resolves against the hook PROCESS's directory, which is
    the session's, and in this workspace that is routinely a different
    repository from the one the command names. Every path test in this file
    used it, so the same command with the same payload `cwd` reached opposite
    verdicts depending on where the session happened to sit: a mkdir of a
    directory that really exists was allowed from claude-env and refused from
    claude-harness, and -- the dangerous direction -- a genuinely new driver
    in repo B was allowed because a file of that name exists in repo A.
    `tests/` and `_invoke.sh` recur in most of these repos, so the false
    allow is the likely one.

    This is defect 32 of the class `_repo_context.py` opens its docstring by
    describing: "31 hooks with the same defect, most of them silent". Found
    by Grace, 2026-09-11, in a file written that day which already imported
    that module for other things.
    """
    path = (path or "").strip().strip('"').strip("'")
    if not path:
        return ""
    return os.path.normpath(os.path.join(base, os.path.expanduser(path)))


def new_test_infrastructure(path, base, content=""):
    """Why `path` brings a new RUNNER into being, or None.

    The docstring above says "is this a test harness" has no mechanical
    answer, and that is true of the general question. These two are not the
    general question, and both are mechanical:

      * is this a driver/runner/config file that DOES NOT EXIST YET?
      * does this create a directory under a tests root that does not exist?

    Both ask whether something new will RUN tests. Neither asks whether a file
    is "a rig". A fixture dropped beside existing ones answers no to both,
    which is the frictionless case the rule explicitly protects: "Adding test
    CASES to a suite that already exists is normal work."

    Existence is the hinge. Editing a driver that is already there is ordinary
    maintenance; calling a new one into being is the blocked act.
    """
    absolute = resolve(path, base)
    if not absolute or os.path.exists(absolute):
        return None

    name = os.path.basename(absolute)
    if DRIVER_NAMES.match(name) and not delegates_to_an_existing_driver(
            content, absolute):
        return f"`{name}` is a test driver, and it does not exist yet"

    parent = os.path.dirname(absolute)
    if (TEST_ROOT.search(parent) and not os.path.isdir(parent)
            and not inside_an_established_suite(absolute)):
        return f"{parent} is under a test root that does not exist yet"
    return None


# Every spelling of "the directory this script is in". These are inert --
# parameter expansion, or a dirname of $0 -- and must be stripped before the
# substitution scan as well as substituted for the target. Enumerating them
# in ONE place is the point: the round-4 regression was two lists that had
# drifted, one stripping two spellings and one substituting five.
INERT_DIRNAME = ('$(dirname "$0")', "$(dirname '$0')", "$(dirname $0)",
                 "${0%/*}", "`dirname $0`", '`dirname "$0"`',
                 "`dirname '$0'`")


def delegates_to_an_existing_driver(content, absolute):
    """True when this 'driver' only points at a runner that already exists.

    `_invoke.sh` is in DRIVER_NAMES because a driver is what it usually is.
    But the established shape here is three lines that exec a shared driver,
    and calling that "bringing a runner into being" is not true -- the runner
    already exists and is being pointed at. Blocking it made the repo's own
    fixture layout unreachable (Grace, finding 7).

    A driver with a BODY is still refused. The test is deliberately strict:
    short, and containing an exec of something that is already on disk.
    """
    if not content or len(content) > 400:
        return False
    lines = [ln.strip() for ln in content.splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    lines = [ln for ln in lines if not ln.startswith("#!")]
    if len(lines) != 1 or not lines[0].startswith("exec "):
        return False
    # normpath first: the directory this driver would live in usually does
    # not exist yet, so a lexical `..` must be collapsed before globbing or
    # the pattern resolves against nothing.
    here = os.path.dirname(absolute)
    parent = os.path.normpath(os.path.join(here, ".."))
    drivers = {os.path.realpath(d)
               for d in glob.glob(os.path.join(parent, "_*_driver.sh"))}
    if not drivers:
        return False

    # And it must exec one of THEM. Checking only that some driver exists
    # nearby let `exec /tmp/rig/payload_driver.sh` through -- a delayed rig
    # that runs whenever the suite next does (CE-13.4 QA round 2). Grace's
    # wording was "an exec of an existing driver"; this now checks the target.
    # Grace's wording is a file whose ONLY executable line is an exec of an
    # existing driver. Resolving the target and ignoring the rest of the line
    # is not that: `exec <real driver> "$@" <(bash /tmp/payload.sh)` put the
    # real driver in target position while the process substitution ran the
    # payload at suite time -- the same delayed rig the absolute-target check
    # had just closed (CE-13.4 QA round 3). Word expansion happens before
    # exec, so any substitution anywhere on the line is a second command.
    line = lines[0]
    # Strip EVERY inert spelling before scanning for substitutions. The
    # round-3 fix stripped two of the five the loop below still enumerates,
    # so `${0%/*}`, `$(dirname '$0')` and the backtick form started being
    # refused where they had been allowed -- a 0->2 regression written by
    # that commit, which partially re-erected the wall finding 7 removed
    # (CE-13.4 QA round 4). Three of the loop's branches were dead code.
    scan = line
    for spelling in INERT_DIRNAME:
        scan = scan.replace(spelling, "")
    for construct in ("$(", "<(", ">(", "`", "${"):
        if construct in scan:
            return False

    # Substitute BEFORE splitting: `$(dirname "$0")` contains a space, so
    # splitting on whitespace first tears it in half.
    for spelling in INERT_DIRNAME:
        line = line.replace(spelling, here)
    words = line.split()
    if len(words) < 2:
        return False
    target = words[1].strip('"').strip("'")
    return os.path.realpath(os.path.normpath(
        os.path.join(here, target))) in drivers


def inside_an_established_suite(absolute):
    """True when a tests root ABOVE this path already holds a runner.

    The runner discovers fixtures by globbing directories under its tests
    root, so every new hook needs a new directory there and most need a
    three-line driver that only execs a shared one. Refusing that made the
    repo's own fixture layout unreachable: the only actor who could add a
    hook's first fixture was Patrick, from his own terminal, every time.

    So the question is not "is this a new directory under tests" -- it is
    "is a test harness being brought into being". A tests root that already
    contains a runner is an established harness, and adding a suite to it is
    the normal case, exactly once per hook (Grace, finding 7).
    """
    here = os.path.dirname(absolute)
    while True:
        if TEST_ROOT.search(here) and os.path.isdir(here):
            if glob.glob(os.path.join(here, "run-*test*.sh")) or \
                    glob.glob(os.path.join(here, "_*_driver.sh")):
                return True
        parent = os.path.dirname(here)
        if parent == here:
            return False
        here = parent


def new_test_directory(path, base):
    """Why `mkdir path` creates a new TESTS ROOT, or None."""
    absolute = resolve(path, base)
    if not absolute or os.path.isdir(absolute):
        return None
    if not (TEST_ROOT.search(absolute)
            or TEST_ROOT.search(os.path.dirname(absolute))):
        return None
    if inside_an_established_suite(absolute):
        return None
    return f"{absolute} is a test root that does not exist yet"


def infra_refusal(path, why):
    return (
        "\n[shadow_command_guard] BLOCKED: this builds the thing that RUNS "
        "tests.\n"
        f"  {path}\n"
        f"  ({why})\n\n"
        "Building a runner unasked is a hard block:\n\n"
        "  \"Adding test CASES to a suite that already exists is normal"
        " work.\n"
        "   Building the thing that RUNS them is not: a new test directory,\n"
        "   runner, driver, harness, fixture format, or shared test module\n"
        "   requires Patrick's explicit approval BEFORE you write a line of"
        " it.\"\n\n"
        "The way forward is the rule's own: ship the fix and SAY it needs\n"
        "infrastructure. If a criterion cannot be checked without a rig, the\n"
        "criterion is what is wrong, and saying so is the work -- not"
        " building\n"
        "the rig quietly and reporting a pass.\n\n"
        "Adding a fixture to a suite that already exists is untouched by"
        " this,\n"
        "and so is editing a driver that is already there."
    )


def directories_created(command, base):
    """Paths this command would bring into being as a DIRECTORY.

    `mkdir` is the obvious spelling and was the only one checked. The one
    that walked around it is `mkdir /tmp/p && mv /tmp/p <tests>/new_guard`:
    a directory prepared elsewhere and moved in is a new test directory, and
    no token near the tests root says mkdir (CE-2.19 QA round 1).
    """
    made, found = set(), []
    for text in _shell_texts(command):
        for statement in statements(strip_heredoc_bodies(text, False)):
            try:
                tokens = shlex.split(statement)
            except ValueError:
                continue
            argv, _ = strip_wrappers(tokens)
            if not argv:
                continue
            argv0 = os.path.basename(argv[0])
            operands = [x for x in argv[1:] if not x.startswith("-")]
            if argv0 == "mkdir" or (argv0 == "install" and "-d" in argv):
                made.update(resolve(x, base) for x in operands)
                found += operands
            elif argv0 == "git" and git_subcommand(argv)[0] == "clone":
                # A clone brings a directory into being like mkdir does.
                rest = git_subcommand(argv)[1]
                if len(rest) > 1:
                    found += rest[1:]
            elif argv0 in EXTRACT_DEST:
                dest = _flag_value(argv, EXTRACT_DEST[argv0])
                if dest:
                    found.append(dest)
            elif argv0 in ("mv", "cp", "rsync") and len(operands) > 1:
                # A source that is a directory now, or that an earlier
                # statement in this same command just made one.
                for source in operands[:-1]:
                    resolved = resolve(source, base)
                    if os.path.isdir(resolved) or resolved in made:
                        found.append(operands[-1])
                        break
    return found


def refusal(name, path, why):
    return (
        f"\n[shadow_command_guard] BLOCKED: this creates a `{name}` that would "
        f"be found instead of the real one.\n"
        f"  {path}\n"
        f"  ({why})\n\n"
        "A stub named after a real command, reachable before it, is the shape\n"
        "every test rig takes -- and building one unasked is a hard block:\n\n"
        "  \"Adding test CASES to a suite that already exists is normal work.\n"
        "   Building the thing that RUNS them is not: a new test directory,\n"
        "   runner, driver, harness, fixture format, or shared test module\n"
        "   requires Patrick's explicit approval BEFORE you write a line of it.\"\n\n"
        "The way forward is the rule's own: ship the fix and SAY it needs\n"
        "infrastructure. If a criterion cannot be checked without a rig, the\n"
        "criterion is what is wrong, and saying so is the work -- not building\n"
        "the rig quietly and reporting a pass.\n\n"
        "Editing the real file where it lives is untouched by this."
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, EOFError):
        return ALLOW

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return ALLOW

    # The repo the COMMAND is about, not the directory this process happens to
    # sit in. See resolve() -- every path test here used the latter.
    session = payload.get("cwd") or os.getcwd()

    if tool in ("Write", "Edit"):
        path = tool_input.get("file_path") or ""
        # A Write is runnable only if its CONTENT is a program. Writing data
        # to a file named `env` is not building a shadow of anything.
        content = (tool_input.get("content")
                   or tool_input.get("new_string") or "")
        name = shadowed(path, session, bool(SHEBANG.match(content.lstrip())))
        # A Write carries no PATH, so the only question is whether it lands
        # somewhere a project would keep it.
        if name and not in_a_work_tree(path, session):
            print(refusal(name, path, "written outside any git work tree"),
                  file=sys.stderr)
            return BLOCK
        why = new_test_infrastructure(path, session, content)
        if why:
            print(infra_refusal(path, why), file=sys.stderr)
            return BLOCK
        return ALLOW

    if tool == "Bash":
        command = tool_input.get("command") or ""
        base = target_directory(command, default=session)
        for kind, name in redefinitions(command):
            print(redefinition_refusal(kind, name), file=sys.stderr)
            return BLOCK
        prepends = bool(PATH_PREPEND.search(command))
        # Computed once. Two separate walks over the same command was a
        # second full parse per Bash event for no gain (Grace, finding 19).
        written = created_paths(command, base)
        runnable = runnable_targets(command, base)
        # Populating a directory you also put first on PATH is the shadow
        # move, whatever tool does the populating. Watching the DIRECTORY
        # replaces an ever-growing list of ways to put a file in one, and it
        # is what catches tar, unzip, git clone and an interpreter payload
        # alike -- each of which walked past the copier list (QA round 2).
        for first in PATH_DIRS.findall(command):
            target = resolve(first, base).rstrip("/")
            if not target:
                continue
            for path in (written + directories_created(command, base)
                         + _source_literals(command)):
                here = resolve(path, base)
                if here == target or here.startswith(target + "/"):
                    print(refusal("command", path,
                                  "this populates a directory the same "
                                  "command puts first on PATH"),
                          file=sys.stderr)
                    return BLOCK
        for path in written:
            # A PATH prepend IS the proof of runnability, and the strongest
            # there is: the command is arranging for this file to be found
            # and run. Requiring evidence of the exec bit as well let the
            # founding rig through when its source did not exist yet at scan
            # time (fixtures 19 and 20).
            name = shadowed(path, base,
                            prepends or resolve(path, base) in runnable)
            if not name:
                continue
            if prepends:
                print(refusal(name, path,
                              "and this command puts its directory first on PATH"),
                      file=sys.stderr)
                return BLOCK
            if not in_a_work_tree(path, base):
                print(refusal(name, path, "written outside any git work tree"),
                      file=sys.stderr)
                return BLOCK
        for path, here in _infra_candidates(command, session):
            why = new_test_infrastructure(path, here)
            if why:
                print(infra_refusal(path, why), file=sys.stderr)
                return BLOCK
        for path in directories_created(command, base):
            why = new_test_directory(path, base)
            if why:
                print(infra_refusal(path, why), file=sys.stderr)
                return BLOCK
        return ALLOW

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
