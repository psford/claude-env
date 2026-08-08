#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block dangerous git and destructive operations.

Enforces CLAUDE.md rules:
- NEVER commit directly to main
- NEVER merge to main via CLI
- NEVER push to main (any refspec landing on main is a CLI merge)
- NEVER push --force to main
- NEVER merge main INTO develop (reverse merge)
- NEVER git reset --hard (destroyed Bloomberg terminal work)
- NEVER git checkout . / git restore . (discards uncommitted changes)
- NEVER git clean -f (deletes untracked files)
- NEVER rm -rf on project directories

This hook BLOCKS these operations with exit code 2.
"""

import json
import sys
import re
import shlex
import subprocess

PROTECTED_BRANCHES = {"main", "master"}

# Shell separators that start a new command in a compound invocation.
STATEMENT_SPLIT = re.compile(r'&&|\|\||[;\n|]')


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

    for statement in STATEMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            # Unbalanced quotes -- fail closed if this looks like a push at all.
            if re.search(r'\bgit\b.*\bpush\b', statement, re.IGNORECASE):
                destinations.update(PROTECTED_BRANCHES)
            continue

        if len(tokens) < 2 or tokens[0] != "git" or "push" not in tokens:
            continue

        args = tokens[tokens.index("push") + 1:]
        deleting = any(a in ("--delete", "-d") for a in args)
        positional = [a for a in args if not a.startswith("-")]

        # First positional after `push` is the remote; the rest are refspecs.
        refspecs = positional[1:] if len(positional) > 1 else []

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


def get_current_branch():
    """Get the current git branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return None

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
    current_branch = get_current_branch()

    # ── DESTRUCTIVE OPERATIONS (blocked on ALL branches) ──

    # Block: git reset --hard (any branch, any args)
    if re.search(r'\bgit\b.*\breset\b.*--hard\b', command, re.IGNORECASE):
        print("BLOCKED: git reset --hard is forbidden. Destroyed uncommitted work before.", file=sys.stderr)
        print("Use 'git stash' to save changes, or 'git merge'/'git rebase' to sync.", file=sys.stderr)
        return 2

    # Block: git checkout . / git checkout -- . (discards all uncommitted changes)
    if re.search(r'\bgit\b.*\bcheckout\b\s+[\-\-\s]*\.\s*$', command, re.IGNORECASE):
        print("BLOCKED: git checkout . discards all uncommitted changes.", file=sys.stderr)
        print("Use 'git stash' to save changes first.", file=sys.stderr)
        return 2

    # Block: git restore . (discards all uncommitted changes)
    if re.search(r'\bgit\b.*\brestore\b\s+\.\s*$', command, re.IGNORECASE):
        print("BLOCKED: git restore . discards all uncommitted changes.", file=sys.stderr)
        print("Use 'git stash' to save changes first.", file=sys.stderr)
        return 2

    # Block: git clean -f (deletes untracked files)
    if re.search(r'\bgit\b.*\bclean\b.*-[a-zA-Z]*f', command, re.IGNORECASE):
        print("BLOCKED: git clean -f deletes untracked files permanently.", file=sys.stderr)
        return 2

    # Block: rm -rf (any directory — too dangerous to allow anywhere)
    if re.search(r'\brm\b\s+.*-[a-zA-Z]*r[a-zA-Z]*f', command, re.IGNORECASE):
        print("BLOCKED: rm -rf is forbidden. Too dangerous to run unattended.", file=sys.stderr)
        return 2

    # Block: Windows equivalents of rm -rf
    if re.search(r'\brd\b\s+/s', command, re.IGNORECASE):
        print("BLOCKED: rd /s is forbidden (Windows rm -rf equivalent).", file=sys.stderr)
        return 2
    if re.search(r'\bRemove-Item\b.*-Recurse', command, re.IGNORECASE):
        print("BLOCKED: Remove-Item -Recurse is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bdel\b\s+/[sS]', command, re.IGNORECASE):
        print("BLOCKED: del /s is forbidden (recursive delete).", file=sys.stderr)
        return 2

    # Block: git push --force on ANY branch (can destroy remote history)
    if re.search(r'\bgit\b.*\bpush\b.*--force\b', command, re.IGNORECASE):
        print("BLOCKED: git push --force is forbidden on any branch.", file=sys.stderr)
        return 2

    # Block: SQL destructive operations
    if re.search(r'\bDROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)\b', command, re.IGNORECASE):
        print("BLOCKED: DROP TABLE/DATABASE/SCHEMA is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bTRUNCATE\s+TABLE\b', command, re.IGNORECASE):
        print("BLOCKED: TRUNCATE TABLE is forbidden.", file=sys.stderr)
        return 2
    if re.search(r'\bDELETE\s+FROM\b(?!.*\bWHERE\b)', command, re.IGNORECASE):
        print("BLOCKED: DELETE FROM without WHERE clause is forbidden.", file=sys.stderr)
        return 2

    # ── MAIN BRANCH PROTECTIONS ──

    # Block: git commit on main
    if current_branch == "main" and re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        print("BLOCKED: Direct commits to main are forbidden.", file=sys.stderr)
        print("Switch to develop: git checkout develop", file=sys.stderr)
        return 2

    # Block: git merge main (on develop) - reverse merge
    if current_branch == "develop" and re.search(r'\bgit\b.*\bmerge\b.*\bmain\b', command, re.IGNORECASE):
        print("BLOCKED: Merging main INTO develop is forbidden.", file=sys.stderr)
        print("Git flow: develop -> main via PR, never reverse.", file=sys.stderr)
        return 2

    # Block: git pull origin main (on develop) - also a reverse merge
    if current_branch == "develop" and re.search(r'\bgit\b.*\bpull\b.*\bmain\b', command, re.IGNORECASE):
        print("BLOCKED: Pulling main into develop is forbidden.", file=sys.stderr)
        return 2

    # Block: gh pr merge (CLI merge to main)
    if re.search(r'\bgh\b.*\bpr\b.*\bmerge\b', command, re.IGNORECASE):
        print("BLOCKED: Merging PRs via CLI is forbidden.", file=sys.stderr)
        print("Patrick must merge via GitHub web interface.", file=sys.stderr)
        return 2

    # Block: git push --force to main
    if re.search(r'\bgit\b.*\bpush\b.*--force\b.*\bmain\b', command, re.IGNORECASE):
        print("BLOCKED: Force push to main is forbidden.", file=sys.stderr)
        return 2

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
    if current_branch == "develop" and re.search(r'\bgit\b.*\brebase\b.*\bmain\b', command, re.IGNORECASE):
        print("BLOCKED: Rebasing develop on main is forbidden.", file=sys.stderr)
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main())
