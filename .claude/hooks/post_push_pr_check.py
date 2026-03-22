#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: After any git push, check PR state and inject reminder.

Problem this solves:
  After pushing commits to develop, Claude incorrectly referenced already-merged PRs
  instead of creating new ones. This happened 3 times (PRs #88, #89) because no hook
  fired — the PreToolUse hook only catches `gh pr edit`, not `git push`.

Solution:
  After every `git push`, this hook checks whether the current branch has an OPEN PR
  to main. If no open PR exists (either no PR at all, or the last one was merged/closed),
  it injects a HARD BLOCK reminder that forces Claude to create a new PR before
  referencing any PR number.

Hook event: PostToolUse (fires AFTER the tool completes)
Matcher: Bash (only git push commands)
"""

import json
import sys
import re
import subprocess


def get_current_branch():
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_open_pr_for_branch(branch):
    """Check if a branch has an OPEN PR to main. Returns (number, state) or (None, None)."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--base", "main",
             "--state", "open", "--json", "number", "--jq", ".[0].number"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip()), "OPEN"
    except Exception:
        pass
    return None, None


def get_most_recent_pr_for_branch(branch):
    """Get the most recently updated PR for this branch (any state)."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--base", "main",
             "--state", "all", "--json", "number,state",
             "--jq", ".[0] | \"\\(.number) \\(.state)\""],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return int(parts[0]), parts[1]
    except Exception:
        pass
    return None, None


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

    # Only care about git push commands
    if not re.search(r'\bgit\b.*\bpush\b', command, re.IGNORECASE):
        return 0

    branch = get_current_branch()
    if not branch or branch == "main":
        return 0

    # Check if there's an OPEN PR for this branch
    open_pr, _ = get_open_pr_for_branch(branch)

    if open_pr:
        # There IS an open PR — safe to reference it
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"PR #{open_pr} is OPEN for branch '{branch}'. You may reference this PR."
            }
        }
        print(json.dumps(output))
        return 0

    # No open PR — check if there's a merged/closed one
    recent_pr, recent_state = get_most_recent_pr_for_branch(branch)

    if recent_pr and recent_state == "MERGED":
        # CRITICAL: The most recent PR was already merged. Claude MUST NOT reference it.
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"""
⚠️ MANDATORY PR CHECK — READ THIS BEFORE RESPONDING ⚠️

You just pushed to '{branch}', but the most recent PR (#{recent_pr}) is ALREADY MERGED.

RULES:
1. Do NOT say "PR #{recent_pr} now has N commits" — it is MERGED and DONE.
2. Do NOT reference PR #{recent_pr} in any way as if it contains your new commits.
3. If these commits need to go to production, you MUST create a NEW PR:
   gh pr create --title "..." --body "..." --base main --head {branch}
4. Tell the user: "These commits need a new PR to reach main."

VIOLATION OF THESE RULES HAS CAUSED PRODUCTION INCIDENTS. THIS IS NON-NEGOTIABLE.
"""
            }
        }
        print(json.dumps(output))
    elif not recent_pr:
        # No PR at all — just a heads up
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"No PR exists for branch '{branch}' → main. If deployment is needed, create one with: gh pr create --base main --head {branch}"
            }
        }
        print(json.dumps(output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
