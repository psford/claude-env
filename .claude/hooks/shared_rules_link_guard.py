#!/usr/bin/env python3
"""PreToolUse/Bash guard: refuse a commit in a repo that inherits no shared rules.

THE FAILURE THIS EXISTS FOR.

Eleven repos consumed `claude-env/shared/claude-md/00-universal.md` and every
one of them held its own COPY. Nothing compared them. On 2026-08-30 a rule was
added to that fragment: all eleven were in sync a second before, ten were stale
a second after, and nothing anywhere would have said so. One repo noticed within
the hour, and only because it happened to own a test asserting its own
CLAUDE.md was current.

CE-5 removed the cause. A fragment carrying no {{VARS}} is byte-identical in
every repo, so it is now a symlink at `.claude/rules/<name>.md` pointing into
claude-env. One file. Nothing to disagree with.

WHICH CHANGES THE FAILURE MODE, AND MAKES IT QUIETER. Drift was two files
disagreeing -- visible in a diff, findable by comparison. Absence is a repo
whose link is missing or dangling: it inherits NOTHING while looking exactly
like a healthy one. There is no second copy to compare against, because
removing the second copy was the point.

`sync-claude-md.sh --check` already detects all three broken shapes -- not a
symlink, dangling, pointing somewhere other than the source -- and exits 3.
Until this guard it ran nowhere, which is the same gap one level up: a detector
nobody invokes is worth exactly as much as the drift check that was wired into
none of eleven repos.

WHY HERE AND NOT IN EACH REPO'S OWN HOOKS. Wiring a check into eleven repos is
the distribution problem this epic exists to kill. The check lives once, in
claude-env, and is wired once in ~/.claude/settings.json -- the same shape as
every other guard here, and the same shape as the links themselves.

WHY COMMIT AND NOT SESSION START. A session-start warning is read by whoever is
watching. A commit is the artifact that persists, and a commit made under rules
the repo never received is the thing worth refusing.
"""
import json
import os
import re
import shlex
import subprocess
import sys

ESCAPE = "SHARED_RULES_OK"

CLAUDE_ENV = "/home/patrick/projects/claude-env"
SYNC = os.path.join(CLAUDE_ENV, "helpers", "sync-claude-md.sh")

GIT = re.compile(r'(?:^|/)git$')
ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*=')


def target_repo(command, default):
    """The directory the command is about.

    NOTE: this duplicates target_directory() in claude-harness's _shell.py and
    in main_branch_guard, and inherits its known limitation -- a path written
    with a shell variable (`git -C $d`) is an unexpanded string, resolves to
    nothing, and falls back to `default`. Filed as CH-192.2. It is copied
    rather than fixed here because fixing one copy and not the others is how
    two guards came to disagree about the same question once already; the fix
    belongs in all of them at once.
    """
    cwd = default or os.getcwd()
    explicit = None
    for statement in re.split(r'&&|\|\||;|\|', command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            moved = os.path.normpath(os.path.join(cwd, os.path.expanduser(tokens[1])))
            if os.path.isdir(moved):
                cwd = moved
        while tokens and ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        if tokens and GIT.search(tokens[0]) and "-C" in tokens:
            idx = tokens.index("-C")
            if idx + 1 < len(tokens):
                named = os.path.normpath(
                    os.path.join(cwd, os.path.expanduser(tokens[idx + 1])))
                if os.path.isdir(named):
                    explicit = named
    return explicit or cwd


def is_a_commit(command):
    for statement in re.split(r'&&|\|\||;', command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        # Leading VAR=VALUE assignments belong to the shell, not to git.
        # Without this, `SHARED_RULES_OK=1 git commit` was not recognised as a
        # commit AT ALL -- which made the escape-hatch fixture pass for the
        # wrong reason and, far worse, meant ANY env prefix silently evaded the
        # guard. A control that could not fail is what surfaced it: removing
        # the escape hatch changed nothing, because the hatch was never what
        # let that fixture through.
        while tokens and ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        # `git -C x commit` and `git commit` both, so the flag does not hide
        # the verb.
        if len(tokens) >= 2 and GIT.search(tokens[0]) and "commit" in tokens[1:]:
            return True
    return False


def repo_root(path):
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=path, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our business to fail a malformed event

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command or ESCAPE in command:
        return 0
    if not is_a_commit(command):
        return 0

    root = repo_root(target_repo(command, payload.get("cwd")))
    if not root:
        return 0  # not a git repo: nothing to inherit into

    # A repo that consumes no fragments is not opted in, and must stay silent.
    # Most directories on this machine are in that category.
    if not os.path.isfile(os.path.join(root, ".claude", "claude-md.json")):
        return 0

    if not os.path.isfile(SYNC):
        # Deliberately NOT a silent pass. If claude-env is gone then every link
        # in this repo dangles and it is inheriting nothing -- which is exactly
        # the state this guard exists to refuse. "Skipping, not installed"
        # exiting 0 is failure wearing a success mask.
        print("BLOCKED: the shared rules cannot be verified.", file=sys.stderr)
        print(file=sys.stderr)
        print(f"  {SYNC} is missing, so every .claude/rules link in this repo",
              file=sys.stderr)
        print("  points at nothing and no shared rule is being inherited.",
              file=sys.stderr)
        print(file=sys.stderr)
        print(f"  Restore claude-env at {CLAUDE_ENV}, or commit with "
              f"{ESCAPE}=1 in the command if you have decided this repo",
              file=sys.stderr)
        print("  should stop consuming shared rules.", file=sys.stderr)
        return 2

    try:
        out = subprocess.run(["bash", SYNC, "--check", root],
                             capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"BLOCKED: could not run the shared-rules check: {exc}",
              file=sys.stderr)
        return 2

    if out.returncode == 0:
        return 0

    print("BLOCKED: this repo is not inheriting the shared rules.", file=sys.stderr)
    print(file=sys.stderr)
    for line in (out.stderr or "").splitlines():
        print(f"  {line}", file=sys.stderr)
    print(file=sys.stderr)
    print("  A missing or dangling link means this repo inherits NOTHING while",
          file=sys.stderr)
    print("  looking exactly like a healthy one. Repair it with:", file=sys.stderr)
    print(file=sys.stderr)
    print(f"    {SYNC} {root}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  Bypass with {ESCAPE}=1 in the command. Say why in the commit",
          file=sys.stderr)
    print("  message if you do -- a bypass nobody explained is one nobody can",
          file=sys.stderr)
    print("  review.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
