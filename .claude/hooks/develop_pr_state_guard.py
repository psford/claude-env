#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Develop PR state guard.

Fires on git push. Blocks push to develop when the most recent PR from develop
to main is merged AND develop has commits ahead of origin/main. Uses gh pr list
to check PR state.

Exit codes:
  0 = allow push
  2 = block push (with stderr message)
"""

import json
import subprocess
import sys
import time


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git push" not in command:
        return 0

    # Skip --dry-run
    if "--dry-run" in command or "-n " in command:
        return 0

    # Check if we're on develop branch
    current_branch = get_current_branch()
    if current_branch != "develop":
        return 0  # Other branches handled by pre_push_merged_branch_guard.py

    # Check if there's an open PR from develop to main
    open_pr_count = get_open_pr_count()
    if open_pr_count > 0:
        return 0  # Open PR exists, safe to push

    # Check commits ahead of origin/main
    commits_ahead = get_commits_ahead()
    if commits_ahead == 0:
        return 0  # No commits ahead, safe to push

    # Get most recent PR state
    pr_state = get_most_recent_pr_state()
    if pr_state in ("MERGED", "CLOSED"):
        print("\n❌ DEVELOP PR STATE GUARD: Most recent PR is merged/closed but develop has unpushed commits", file=sys.stderr)
        print("   Create a new PR before pushing to develop (no direct pushes after merge).\n", file=sys.stderr)
        print(f"   Commits ahead of origin/main: {commits_ahead}", file=sys.stderr)
        print(f"   Most recent PR state: {pr_state}", file=sys.stderr)
        print("\n   Fix: Create new PR via `gh pr create --base main --head develop`", file=sys.stderr)
        return 2

    return 0


def get_current_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_open_pr_count():
    """Check number of open PRs from develop to main."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", "develop", "--base", "main", "--state", "open", "--json", "number"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return len(data) if isinstance(data, list) else 0
            except json.JSONDecodeError:
                return 0
        return 0
    except Exception:
        return 0


def get_commits_ahead():
    """Get number of commits develop has ahead of origin/main."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..develop"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            try:
                return int(result.stdout.strip())
            except ValueError:
                return 0
        return 0
    except Exception:
        return 0


def get_most_recent_pr_state():
    """Get the state of the most recent PR from develop to main."""
    try:
        # Get list of PRs (both open and closed) from develop to main, sorted by creation date descending
        result = subprocess.run(
            ["gh", "pr", "list", "--head", "develop", "--base", "main", "--state", "all", "--json", "state,number", "--limit", "1"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("state", "UNKNOWN").upper()
            except json.JSONDecodeError:
                pass
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


if __name__ == "__main__":
    sys.exit(main())
