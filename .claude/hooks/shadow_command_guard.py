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
from _repo_context import statements, strip_heredoc_bodies  # noqa: E402,I001

BLOCK = 2
ALLOW = 0

# `d=/tmp/x` then `PATH=$d:$PATH` is the same move split across statements, so
# the prepend is matched against the whole command rather than per statement.
PATH_PREPEND = re.compile(r'\bPATH\s*=\s*(?!\$PATH\b)[^\s;|&]*[:$]')

REDIRECT = re.compile(r'>\|?\s*([^\s;|&<>]+)')
COPIERS = ("cp", "mv", "ln", "install", "tee")


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


def created_paths(command):
    """Paths this command would create, copy to, or make executable."""
    found = []
    for statement in statements(strip_heredoc_bodies(command, False)):
        found += REDIRECT.findall(statement)
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        if not tokens:
            continue
        argv0 = os.path.basename(tokens[0])
        if argv0 in COPIERS and len(tokens) > 1:
            found.append(tokens[-1])
        if argv0 == "chmod" and len(tokens) > 2:
            found += tokens[2:]
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
        return ALLOW

    if tool == "Bash":
        command = tool_input.get("command") or ""
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
        return ALLOW

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
