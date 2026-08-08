#!/usr/bin/env python3
"""Which repository is this hook actually about?

A hook process inherits the session's working directory. In a multi-repo
workspace that is routinely a *different* repository from the one the command
touches, so a hook that runs `git diff --cached` inspects the wrong index and
finds nothing. It does not fail loudly -- it passes, vacuously, which is worse.

Found on 2026-08-08 after main_branch_guard blocked every commit in every repo
because the session sat in claude-env on main. That was the loud symptom;
audit found 31 hooks with the same defect, most of them silent.

Usage in a hook, immediately after reading the payload:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _repo_context import enter_target_repo

    enter_target_repo(hook_input)

After that call, bare `subprocess.run(["git", ...])` inherits the right
directory and every existing call site is correct without being rewritten.
"""

import os
import re
import shlex
import subprocess

STATEMENT_SPLIT = re.compile(r'&&|\|\||[;\n|]')
GIT_INVOCATION = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:sudo\s+)?git\b')
QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')


def statements(command):
    """Split into commands, ignoring separators inside quotes.

    `python3 -c "import json; ..."` is one statement. Splitting at the ';'
    inside the string produces two fragments, neither of which looks like what
    it is.
    """
    masked = QUOTED.sub(lambda m: " " * len(m.group()), command)
    start = 0
    for match in STATEMENT_SPLIT.finditer(masked):
        chunk = command[start:match.start()].strip()
        if chunk:
            yield chunk
        start = match.end()
    tail = command[start:].strip()
    if tail:
        yield tail


def target_directory(command, default=None):
    """The directory the git commands in `command` will run in.

    Honours a leading `cd <path>`, which applies to everything after it, and
    `git -C <path>`, which applies to one invocation and wins as the more
    specific. Unresolvable paths (a shell variable this cannot expand) fall
    back to `default`, which keeps the behaviour conservative rather than
    guessing.
    """
    cwd = default or os.getcwd()
    explicit = None

    def resolve(path, base):
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        return path if os.path.isdir(path) else None

    for statement in statements(command or ""):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            moved = resolve(tokens[1], cwd)
            if moved:
                cwd = moved
        if GIT_INVOCATION.match(statement) and "-C" in tokens:
            idx = tokens.index("-C")
            if idx + 1 < len(tokens):
                named = resolve(tokens[idx + 1], cwd)
                if named:
                    explicit = named

    return explicit or cwd


def enter_target_repo(hook_input):
    """chdir to the repo the command is about. Returns the directory.

    Call this once, early. Every subsequent bare git call is then correct
    without touching the call site -- which is why 28 hooks could be fixed
    without rewriting their internals.
    """
    tool_input = (hook_input or {}).get("tool_input") or {}
    command = tool_input.get("command", "")
    session_cwd = (hook_input or {}).get("cwd") or os.getcwd()
    target = target_directory(command, default=session_cwd)
    try:
        os.chdir(target)
    except OSError:
        return os.getcwd()
    return target


def current_branch(cwd=None):
    """Current branch, or None if it cannot be determined.

    `branch --show-current` rather than `rev-parse --abbrev-ref HEAD`: rev-parse
    fails on an unborn branch, which made the first commit in a new repo
    impossible once undetectable branches began failing closed.

    A detached HEAD reports empty and is returned as None -- it could be
    sitting on the trunk's commit and there is no way to prove otherwise.
    """
    for argv in (["git", "branch", "--show-current"],
                 ["git", "rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=5, cwd=cwd or os.getcwd())
        except Exception:
            return None
        if r.returncode == 0:
            return r.stdout.strip() or None
    return None


def repo_root(cwd=None):
    """Top level of the work tree containing `cwd`, or None."""
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5,
                           cwd=cwd or os.getcwd())
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
