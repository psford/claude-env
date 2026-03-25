#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block branch/worktree creation from main when
develop has unmerged commits.

Enforces git flow rule:
- develop -> main via PR, never the reverse
- Feature branches may come from either, but if develop is ahead of main,
  branching from main means the new branch is missing in-progress work.

This hook BLOCKS these operations with exit code 2 and shows the divergent
commits so the author knows exactly what they would be skipping.
"""

import json
import sys
import re
import subprocess


def run(args, timeout=10):
    """Run a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_branch():
    """Return the name of the currently checked-out branch, or None."""
    rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc == 0 and out and out != "HEAD":
        return out
    return None


def is_branch_creation_from_main(command):
    """
    Return (True, base_type) if the command creates a branch or worktree
    whose starting point is main (explicitly or implicitly via HEAD).
    """
    cmd = re.sub(r'\s+', ' ', command.strip())

    explicit_main_patterns = [
        r'\bgit\b.*\bcheckout\b.*\s-b\s+\S+\s+(origin/)?main\b',
        r'\bgit\b.*\bbranch\b\s+\S+\s+(origin/)?main\b',
        r'\bgit\b.*\bswitch\b.*\s-c\s+\S+\s+(origin/)?main\b',
        r'\bgit\b.*\bswitch\b.*\s--create\s+\S+\s+(origin/)?main\b',
        r'\bgit\b.*\bworktree\b.*\badd\b\s+\S+\s+(origin/)?main\b',
        r'\bgit\b.*\bworktree\b.*\badd\b.*\s-b\s+\S+\s+(origin/)?main\b',
    ]

    for pattern in explicit_main_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, "explicit"

    implicit_patterns = [
        r'\bgit\b.*\bcheckout\b.*\s-b\s+\S+\s*$',
        r'\bgit\b.*\bbranch\b\s+\S+\s*$',
        r'\bgit\b.*\bswitch\b.*\s-c\s+\S+\s*$',
        r'\bgit\b.*\bswitch\b.*\s--create\s+\S+\s*$',
        r'\bgit\b.*\bworktree\b.*\badd\b\s+\S+\s*$',
        r'\bgit\b.*\bworktree\b.*\badd\b\s+\S+\s+-b\s+\S+\s*$',
    ]

    for pattern in implicit_patterns:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, "implicit"

    return False, None


def fetch_remote(timeout=15):
    """Fetch origin quietly. Failures are non-fatal."""
    try:
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            capture_output=True, timeout=timeout
        )
    except Exception:
        pass


def get_divergent_commits():
    """
    Return commits on origin/develop but NOT on origin/main.
    Empty list if in sync or refs don't exist.
    """
    for ref in ("origin/main", "origin/develop"):
        rc, _, _ = run(["git", "rev-parse", "--verify", ref])
        if rc != 0:
            return []

    rc, out, _ = run([
        "git", "log",
        "origin/main..origin/develop",
        "--oneline",
        "--no-decorate",
    ])
    if rc != 0:
        return []

    return [line for line in out.splitlines() if line.strip()]


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not command:
        return 0

    is_creation, base_type = is_branch_creation_from_main(command)
    if not is_creation:
        return 0

    if base_type == "implicit":
        current = get_current_branch()
        if current != "main":
            return 0

    fetch_remote()

    divergent = get_divergent_commits()
    if not divergent:
        return 0

    commit_list = "\n".join(f"  {c}" for c in divergent)
    count = len(divergent)
    noun = "commit" if count == 1 else "commits"

    print(
        f"BLOCKED: develop is {count} {noun} ahead of main.\n"
        f"\n"
        f"Branching from main right now would create a branch that is MISSING\n"
        f"the following in-progress work from develop:\n"
        f"\n"
        f"{commit_list}\n"
        f"\n"
        f"Options:\n"
        f"  1. Branch from develop instead\n"
        f"  2. Merge develop -> main via PR first, then branch from main\n"
        f"  3. If you truly need a hotfix off main, discuss with Patrick first\n",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
