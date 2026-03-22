#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block dangerous git and destructive operations.

Enforces CLAUDE.md rules:
- NEVER commit directly to main
- NEVER merge to main via CLI
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
import subprocess

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

    # Block: git rebase main (on develop)
    if current_branch == "develop" and re.search(r'\bgit\b.*\brebase\b.*\bmain\b', command, re.IGNORECASE):
        print("BLOCKED: Rebasing develop on main is forbidden.", file=sys.stderr)
        return 2

    return 0

if __name__ == "__main__":
    sys.exit(main())
