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

import json
import os
import re
import shlex
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    QUOTED, SHELLS, payload_of, statements, strip_heredoc_bodies,
    strip_wrappers)

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
    r'(?:^|[;&|(\n]\s*)\s*alias\s+([A-Za-z_][A-Za-z0-9_-]*)\s*=')


def shadowed(path):
    """The real command `path` would be found instead of, or None.

    `shutil.which` rather than a hardcoded list: which commands are real is a
    property of the machine, and a list here would be one more thing to drift
    out of date. A path that IS where the command already lives is the real
    file being edited, not a shadow of it.
    """
    base = os.path.basename(path.strip().strip('"').strip("'"))
    if not base or base.startswith("."):
        return None
    real = shutil.which(base)
    if not real:
        return None
    try:
        if os.path.realpath(real) == os.path.realpath(path):
            return None
    except OSError:
        pass
    return base


def in_a_work_tree(path):
    """True when `path` sits inside a git work tree.

    Not a judgement about quality. It is the cheap, honest separator between a
    file that belongs to a project and one written to scratch in order to be
    found first. Walked upward rather than shelling out to git, because this
    runs on every Write.
    """
    here = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(here, ".git")):
            return True
        parent = os.path.dirname(here)
        if parent == here:
            return False
        here = parent


def _destinations(argv0, operands):
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
    if os.path.isdir(target):
        return [os.path.join(target, os.path.basename(s)) for s in sources]
    return [target]


def created_paths(command):
    """Paths this command would create, copy to, or make executable."""
    found = []
    for statement in statements(strip_heredoc_bodies(command, False)):
        found += REDIRECT.findall(statement)
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        argv, _ = strip_wrappers(tokens)
        if not argv:
            continue
        argv0 = os.path.basename(argv[0])
        operands = [t for t in argv[1:] if not t.startswith("-")]
        if argv0 in COPIERS or argv0 == "dd":
            found += _destinations(argv0, operands)
        if argv0 == "git" and "checkout" in argv[1:2] and len(operands) > 1:
            # `git checkout <path>` restores a file from the index. It is not
            # a copier, and it writes one all the same.
            found += operands[1:]
        if argv0 == "chmod" and len(operands) > 1:
            found += operands[1:]
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
            if name and (name in BUILTINS or shutil.which(name)):
                found.append(("function", name))
        for match in ALIAS_DEF.finditer(text):
            name = match.group(1)
            if name and (name in BUILTINS or shutil.which(name)):
                found.append(("alias", name))
    return found


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


def new_test_infrastructure(path):
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
    path = path.strip().strip('"').strip("'")
    if not path:
        return None
    absolute = os.path.abspath(path)
    if os.path.exists(absolute):
        return None

    base = os.path.basename(absolute)
    if DRIVER_NAMES.match(base):
        return f"`{base}` is a test driver, and it does not exist yet"

    parent = os.path.dirname(absolute)
    if TEST_ROOT.search(parent) and not os.path.isdir(parent):
        return f"{parent} is a test directory that does not exist yet"
    return None


def new_test_directory(path):
    """Why `mkdir path` creates a new test directory, or None."""
    path = path.strip().strip('"').strip("'")
    if not path:
        return None
    absolute = os.path.abspath(path)
    if os.path.isdir(absolute):
        return None
    if TEST_ROOT.search(absolute) or TEST_ROOT.search(
            os.path.dirname(absolute)):
        return f"{absolute} is a test directory that does not exist yet"
    return None


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


def directories_created(command):
    """Paths this command would bring into being as a DIRECTORY.

    `mkdir` is the obvious spelling and was the only one checked. The one
    that walked around it is `mkdir /tmp/p && mv /tmp/p <tests>/new_guard`:
    a directory prepared elsewhere and moved in is a new test directory, and
    no token near the tests root says mkdir (CE-2.19 QA round 1).
    """
    made, found = set(), []
    for statement in statements(strip_heredoc_bodies(command, False)):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        argv, _ = strip_wrappers(tokens)
        if not argv:
            continue
        argv0 = os.path.basename(argv[0])
        operands = [t for t in argv[1:] if not t.startswith("-")]
        if argv0 == "mkdir":
            made.update(os.path.abspath(t) for t in operands)
            found += operands
        elif argv0 in ("mv", "cp", "rsync") and len(operands) > 1:
            # A source that is a directory now, or that an earlier statement
            # in this same command just made one.
            for source in operands[:-1]:
                if os.path.isdir(source) or os.path.abspath(source) in made:
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

    if tool in ("Write", "Edit"):
        path = tool_input.get("file_path") or ""
        name = shadowed(path)
        # A Write carries no PATH, so the only question is whether it lands
        # somewhere a project would keep it.
        if name and not in_a_work_tree(path):
            print(refusal(name, path, "written outside any git work tree"),
                  file=sys.stderr)
            return BLOCK
        why = new_test_infrastructure(path)
        if why:
            print(infra_refusal(path, why), file=sys.stderr)
            return BLOCK
        return ALLOW

    if tool == "Bash":
        command = tool_input.get("command") or ""
        for kind, name in redefinitions(command):
            print(redefinition_refusal(kind, name), file=sys.stderr)
            return BLOCK
        prepends = bool(PATH_PREPEND.search(command))
        for path in created_paths(command):
            name = shadowed(path)
            if not name:
                continue
            if prepends:
                print(refusal(name, path,
                              "and this command puts its directory first on PATH"),
                      file=sys.stderr)
                return BLOCK
            if not in_a_work_tree(path):
                print(refusal(name, path, "written outside any git work tree"),
                      file=sys.stderr)
                return BLOCK
        for path in created_paths(command):
            why = new_test_infrastructure(path)
            if why:
                print(infra_refusal(path, why), file=sys.stderr)
                return BLOCK
        for path in directories_created(command):
            why = new_test_directory(path)
            if why:
                print(infra_refusal(path, why), file=sys.stderr)
                return BLOCK
        return ALLOW

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
