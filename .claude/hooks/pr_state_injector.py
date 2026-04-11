#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Inject current PR state on every git/gh command.

Problem this solves:
  Claude remembers the PR state from when it was created and asserts that state
  later without checking. PRs get merged between turns, but Claude says "PR #15
  is open" because it never re-queries. This has been a persistent, recurring
  issue across many sessions.

  The existing post_push_pr_check.py only fires after `git push`. This hook
  fires on ANY git or gh command, ensuring Claude always has fresh PR state
  context injected before responding.

Strategy:
  After any git/gh Bash command, check the current branch's PR state and
  inject it. This is cheap (one gh API call, ~1s) and eliminates the entire
  class of stale-PR-state bugs.

Hook event: PostToolUse (fires AFTER the tool completes)
Matcher: Bash (any git or gh command)
"""

import json
import sys
import re
import subprocess


def get_repo_root():
    """Get the git repo root, or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_current_branch():
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_all_prs_for_branch(branch):
    """Get all PRs (any state) for this branch -> main, most recent first."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--base", "main",
             "--state", "all", "--json", "number,state",
             "--jq", '.[] | "\\(.number) \\(.state)"'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = []
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) == 2:
                    prs.append((int(parts[0]), parts[1]))
            return prs
    except Exception:
        pass
    return []


def count_commits_ahead(branch):
    """Count commits on branch that aren't on origin/main."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"origin/main..{branch}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


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

    # Fire on any git or gh command (broad trigger)
    if not re.search(r'\b(git|gh)\b', command, re.IGNORECASE):
        return 0

    # Skip if this IS a pr state check (avoid recursion)
    if re.search(r'gh\s+pr\s+(list|view)', command, re.IGNORECASE):
        return 0

    # Skip trivial read-only commands that don't change context
    if re.search(r'\bgit\s+(log|diff|show|blame|status)\b', command, re.IGNORECASE):
        return 0

    branch = get_current_branch()
    if not branch or branch == "main":
        return 0

    # Check all PRs for this branch
    prs = get_all_prs_for_branch(branch)
    commits_ahead = count_commits_ahead(branch)

    if not prs:
        if commits_ahead > 0:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"📌 PR STATE: Branch '{branch}' has {commits_ahead} commit(s) "
                        f"ahead of origin/main. No PR exists."
                    )
                }
            }
            print(json.dumps(output))
        return 0

    # Build state summary
    open_prs = [(n, s) for n, s in prs if s == "OPEN"]
    merged_prs = [(n, s) for n, s in prs if s == "MERGED"]

    if open_prs:
        pr_num = open_prs[0][0]
        msg = f"📌 PR STATE (LIVE CHECK): PR #{pr_num} is OPEN for '{branch}' → main."
    elif merged_prs and commits_ahead > 0:
        last_merged = merged_prs[0][0]
        msg = (
            f"📌 PR STATE (LIVE CHECK): Most recent PR #{last_merged} is MERGED. "
            f"Branch '{branch}' has {commits_ahead} unmerged commit(s). "
            f"A NEW PR is needed to get these commits to main."
        )
    elif merged_prs:
        last_merged = merged_prs[0][0]
        msg = (
            f"📌 PR STATE (LIVE CHECK): PR #{last_merged} is MERGED. "
            f"No unmerged commits on '{branch}'."
        )
    else:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
