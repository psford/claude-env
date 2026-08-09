#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block updates to already-merged/closed PRs.

Enforces rule:
- NEVER edit or update a PR that has already been merged or closed
- After a PR is merged, create a NEW PR for any new work

This hook BLOCKS these operations with exit code 2.
"""

import json
import sys
import re
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import enter_target_repo, scannable_text  # noqa: E402


def check_pr_state(pr_number):
    """Check the state of a GitHub PR by number."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state", "--jq", ".state"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()  # OPEN, CLOSED, MERGED
    except Exception:
        pass
    return None


def check_current_branch_pr():
    """Check if the current branch has a PR and return its state + number."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "state,number"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return data.get("state"), data.get("number")
    except Exception:
        pass
    return None, None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    # `gh pr view <n>` resolves the PR against whatever repo the process is
    # standing in. Without this, the hook asked the SESSION's repo about a
    # number belonging to another one: on 2026-08-09 it refused work on
    # claude-harness PR #17 (open, ninety seconds old) because claude-env PR #17
    # is merged. It fails open just as easily -- a merged PR is editable
    # whenever the session repo's same-numbered PR happens to be open.
    #
    # Same defect as the 31 hooks fixed by the cwd audit; this one was missed.
    enter_target_repo(hook_input)

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    # Instructions only. A script or document that quotes a gh pr command is
    # not one, and this hook refused its own verification script on
    # 2026-08-09 for exactly that reason.
    command = scannable_text(tool_input.get("command", ""))

    # Only care about gh pr commands
    if not re.search(r'\bgh\b.*\bpr\b', command, re.IGNORECASE):
        return 0

    # Commands that modify PRs (edit title/body, close, reopen, add review)
    # Note: Must have word boundaries on BOTH sides to avoid matching substrings
    # (e.g., "Editor" contains "edit", "Preview" contains "review")
    modify_keywords = r'(?:edit|close|reopen|review|ready|comment)\b'
    modify_match = re.search(
        r'\bgh\b.*\bpr\b.*\b' + modify_keywords, command, re.IGNORECASE
    )

    if not modify_match:
        return 0

    # Extract PR number if provided (e.g., "gh pr edit 88 --title ...")
    pr_num_match = re.search(
        r'\bgh\b.*\bpr\b.*\b' + modify_keywords + r'\s+(\d+)',
        command, re.IGNORECASE
    )

    if pr_num_match:
        # Explicit PR number given
        pr_number = pr_num_match.group(1)
        state = check_pr_state(pr_number)
        if state and state in ("MERGED", "CLOSED"):
            print(
                f"BLOCKED: PR #{pr_number} is already {state}. "
                f"Cannot modify a {state.lower()} PR.",
                file=sys.stderr
            )
            print(
                "Create a NEW PR for any new work: gh pr create --title ... --base main --head develop",
                file=sys.stderr
            )
            return 2
    else:
        # No PR number — gh defaults to current branch's PR
        state, number = check_current_branch_pr()
        if state and state in ("MERGED", "CLOSED"):
            print(
                f"BLOCKED: Current branch's PR #{number} is already {state}. "
                f"Cannot modify a {state.lower()} PR.",
                file=sys.stderr
            )
            print(
                "Create a NEW PR for any new work: gh pr create --title ... --base main --head develop",
                file=sys.stderr
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
