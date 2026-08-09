#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block dangerous git and destructive operations.

Enforces CLAUDE.md rules:
- NEVER commit directly to main
- NEVER merge to main via CLI
- NEVER push to main (any refspec landing on main is a CLI merge)

Branch checks resolve the repository the command actually targets (honouring
`cd <path>` and `git -C <path>`), not the session's cwd -- in a multi-repo
workspace those are routinely different repos.
- NEVER push --force to main
- NEVER merge main INTO develop (reverse merge)
- NEVER git reset --hard (destroyed Bloomberg terminal work)
- NEVER git checkout . / git restore . (discards uncommitted changes)
- NEVER git clean -f (deletes untracked files)
- NEVER rm -rf on project directories

This hook BLOCKS these operations with exit code 2.
"""

import json
import os
import sys
import re
import shlex
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402
    GIT_INVOCATION, STATEMENT_SPLIT, statements, target_directory, scannable_text,
    current_branch as get_current_branch, commit_tokens,
)

PROTECTED_BRANCHES = {"main", "master"}

# This hook reads the command as text, which means it can be spelled around --
# eval, sh -c, a script file and plumbing all defeat it, as the CH-8
# retrospective demonstrated. It is the ADVISORY layer: fast feedback on an
# honest mistake, never the last line. Enforcement is the state-based git hook
# (shared/git-hooks, installed via helpers/install-git-hooks.sh) and authority is
# server-side branch protection. Say so in the refusal, so nobody reads a block
# here as proof the boundary is airtight.
ADVISORY_NOTE = (
    "\n[advisory layer] This guard reads your command as text and can be spelled "
    "around.\nEnforcement is the git hook (helpers/install-git-hooks.sh); authority "
    "is branch\nprotection on the remote. A refusal here is a warning, not a proof.")

# Shell separators that start a new command in a compound invocation.


# A statement invokes git only if it *begins* with git, allowing leading env
# assignments or sudo. Prose that merely contains the word does not.


FORCE_FLAGS = {"-f", "--force", "--force-with-lease", "--force-if-includes"}


def git_statements(command):
    """Yield the statements in `command` that actually invoke git.

    A commit message or PR body that merely mentions git is prose, not a
    command -- but it arrives in the same string. Matching the whole command
    treats both alike, which on 2026-08-07 made a heredoc quoting a
    forced-push example block its own commit, and made a PR body describing
    this very hook block the command that created it.

    Only a statement beginning with git counts. Text inside a quoted argument
    (a -m message, a --body) survives shlex as a single token and so never
    looks like an invocation.
    """
    for statement in statements(command):
        if GIT_INVOCATION.match(statement):
            yield statement


def forced_push(command):
    """True if `command` contains a real git push carrying a force flag."""
    for statement in git_statements(command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            # Begins with git but will not parse -- fail closed.
            if re.search(r'\bpush\b', statement, re.IGNORECASE):
                return True
            continue
        if "push" in tokens and any(t in FORCE_FLAGS for t in tokens):
            return True
    return False


def push_destinations(command, current_branch):
    """Return the set of branch names a `git push` in `command` would write to.

    Parses refspecs rather than pattern-matching the whole string, because the
    destination can be spelled many ways -- `develop:main`, `HEAD:main`,
    `+develop:main`, `:main`, `--delete main`, or a bare `git push` while
    standing on main. A regex over the raw command misses most of these; that
    hole is how a scaffold commit reached main on 2026-08-07 with every hook
    running correctly.

    Returns an empty set when the command contains no git push.
    """
    destinations = set()

    for statement in git_statements(command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            # Begins with git but will not parse -- fail closed.
            if re.search(r'\bpush\b', statement, re.IGNORECASE):
                destinations.update(PROTECTED_BRANCHES)
            continue

        if "push" not in tokens:
            continue

        args = tokens[tokens.index("push") + 1:]
        deleting = any(a in ("--delete", "-d") for a in args)
        positional = [a for a in args if not a.startswith("-")]

        # First positional after `push` is the remote; the rest are refspecs.
        refspecs = positional[1:] if len(positional) > 1 else []

        if not refspecs and current_branch is None:
            # Bare push with an undetectable branch: it could be main. Fail closed.
            destinations.update(PROTECTED_BRANCHES)
            continue

        if not refspecs:
            # `git push` / `git push origin` pushes the current branch.
            if current_branch:
                destinations.add(current_branch)
            continue

        for refspec in refspecs:
            spec = refspec.lstrip("+")
            # dst is after the colon; without a colon the ref names both sides
            # (or, with --delete, names the remote branch being removed).
            dst = spec.split(":", 1)[1] if ":" in spec else spec
            if dst:
                destinations.add(dst.rsplit("/", 1)[-1])
            elif deleting:
                destinations.add(spec.rsplit("/", 1)[-1])

    return destinations




def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    # The payload's cwd, not the process's. Hooks run with the working directory
    # set to the session's repo, which is frequently not the repo the command is
    # about -- and a bare `git commit` names no directory at all. Reading
    # os.getcwd() there answers "what branch is the session repo on", which is a
    # different question, and it fails OPEN: a commit onto main sailed through
    # because the session happened to sit on a feature branch.
    current_branch = get_current_branch(
        target_directory(command, default=hook_input.get("cwd")))

    # Instructions only: quoted arguments and comments are data. Matching the
    # raw string cannot tell a destructive command from a sentence quoting one,
    # and on 2026-08-08 that refused an analysis script and a bash comment.
    # An interpreter's -c argument is still scanned whole -- see scannable_text.
    scannable = scannable_text(command)

    # ── DESTRUCTIVE OPERATIONS (blocked on ALL branches) ──

    # Block: git reset --hard (any branch, any args)
    if re.search(r'\bgit\b.*\breset\b.*--hard\b', scannable, re.IGNORECASE):
        print("BLOCKED: git reset --hard is forbidden. Destroyed uncommitted work before.", file=sys.stderr)
        print("Use 'git stash' to save changes, or 'git merge'/'git rebase' to sync.", file=sys.stderr)
        return 2

    # Block: git checkout . / git checkout -- . (discards all uncommitted changes)
    if re.search(r'\bgit\b.*\bcheckout\b\s+[\-\-\s]*\.\s*$', scannable, re.IGNORECASE):
        print("BLOCKED: git checkout . discards all uncommitted changes.", file=sys.stderr)
        print("Use 'git stash' to save changes first.", file=sys.stderr)
        return 2

    # Block: git restore . (discards all uncommitted changes)
    if re.search(r'\bgit\b.*\brestore\b\s+\.\s*$', scannable, re.IGNORECASE):
        print("BLOCKED: git restore . discards all uncommitted changes.", file=sys.stderr)
        print("Use 'git stash' to save changes first.", file=sys.stderr)
        return 2

    # Block: git clean -f (deletes untracked files)
    if re.search(r'\bgit\b.*\bclean\b.*-[a-zA-Z]*f', scannable, re.IGNORECASE):
        print("BLOCKED: git clean -f deletes untracked files permanently.", file=sys.stderr)
        return 2

    # Block: rm -rf (any directory — too dangerous to allow anywhere)
    if re.search(r'\brm\b\s+.*-[a-zA-Z]*r[a-zA-Z]*f', scannable, re.IGNORECASE):
        print("BLOCKED: rm -rf is forbidden. Too dangerous to run unattended.", file=sys.stderr)
        return 2

    # Block: Windows equivalents of rm -rf
    if re.search(r'\brd\b\s+/s', scannable, re.IGNORECASE):
        print("BLOCKED: rd /s is forbidden (Windows rm -rf equivalent).", file=sys.stderr)
        return 2
    if re.search(r'\bRemove-Item\b.*-Recurse', scannable, re.IGNORECASE):
        print("BLOCKED: Remove-Item -Recurse is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bdel\b\s+/[sS]', scannable, re.IGNORECASE):
        print("BLOCKED: del /s is forbidden (recursive delete).", file=sys.stderr)
        return 2

    # Block: forced push on ANY branch (can destroy remote history). Checked
    # per-statement so a commit message quoting an example is not mistaken for
    # the act itself. Also catches -f, which the old whole-string regex missed.
    if forced_push(command):
        print("BLOCKED: force-pushing is forbidden on any branch.", file=sys.stderr)
        return 2

    # Block: SQL destructive operations
    if re.search(r'\bDROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)\b', scannable, re.IGNORECASE):
        print("BLOCKED: DROP TABLE/DATABASE/SCHEMA is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bTRUNCATE\s+TABLE\b', scannable, re.IGNORECASE):
        print("BLOCKED: TRUNCATE TABLE is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bDELETE\s+FROM\b(?!.*\bWHERE\b)', scannable, re.IGNORECASE):
        print("BLOCKED: DELETE FROM without WHERE clause is forbidden.", file=sys.stderr)
        return 2

    # ── MAIN BRANCH PROTECTIONS ──

    # FAIL CLOSED: if the branch cannot be determined, a commit or merge might
    # be landing on main and we cannot prove otherwise.
    if current_branch is None:
        for statement in git_statements(command):
            if re.search(r'\b(commit|merge|rebase)\b', statement, re.IGNORECASE):
                print("BLOCKED: cannot determine the target branch. "
                      "Fail-closed: refusing a commit/merge whose branch is unknown.",
                      file=sys.stderr)
                return 2

    # Block: git commit on main
    if current_branch == "main" and commit_tokens(command) is not None:
        print("BLOCKED: Direct commits to main are forbidden.", file=sys.stderr)
        print(ADVISORY_NOTE, file=sys.stderr)
        print("Switch to develop: git checkout develop", file=sys.stderr)
        return 2

    # Block: git merge main (on develop) - reverse merge
    if current_branch == "develop" and re.search(r'\bgit\b.*\bmerge\b.*\bmain\b', scannable, re.IGNORECASE):
        print("BLOCKED: Merging main INTO develop is forbidden.", file=sys.stderr)
        print("Git flow: develop -> main via PR, never reverse.", file=sys.stderr)
        return 2

    # Block: git pull origin main (on develop) - also a reverse merge
    if current_branch == "develop" and re.search(r'\bgit\b.*\bpull\b.*\bmain\b', scannable, re.IGNORECASE):
        print("BLOCKED: Pulling main into develop is forbidden.", file=sys.stderr)
        return 2

    # Block: gh pr merge (CLI merge to main)
    if re.search(r'\bgh\b.*\bpr\b.*\bmerge\b', scannable, re.IGNORECASE):
        print("BLOCKED: Merging PRs via CLI is forbidden.", file=sys.stderr)
        print("Patrick must merge via GitHub web interface.", file=sys.stderr)
        return 2

    # (Force pushes to main are already covered by the forced_push check above,
    # which blocks them on every branch.)

    # Block: ANY push landing on main/master. A fast-forward push of a refspec
    # onto main is a merge to main performed over the CLI -- it puts content on
    # the production branch without a PR, which is what the rule forbids
    # regardless of which git verb spells it.
    blocked_destinations = push_destinations(command, current_branch) & PROTECTED_BRANCHES
    if blocked_destinations:
        target = sorted(blocked_destinations)[0]
        print(f"BLOCKED: This pushes to '{target}'. Any refspec landing on "
              f"{'/'.join(sorted(PROTECTED_BRANCHES))} is a CLI merge to the "
              f"production branch.", file=sys.stderr)
        print("Push your branch and open a PR; Patrick merges via GitHub web.", file=sys.stderr)
        print("Seeding a new repo's main is still a PR-less merge -- ask first.", file=sys.stderr)
        return 2

    # Block: git rebase main (on develop)
    if current_branch == "develop" and re.search(r'\bgit\b.*\brebase\b.*\bmain\b', scannable, re.IGNORECASE):
        print("BLOCKED: Rebasing develop on main is forbidden.", file=sys.stderr)
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main())
