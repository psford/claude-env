#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Guard git commit operations.

Enforces CLAUDE.md rules:
- Must show status, diff, log before commit
- Must wait for explicit user approval
- Specs should be updated with code

EXCEPTION: Feature branches off develop are auto-approved.
Claude can commit freely to feature/* branches without user approval.
This enables autonomous implementation plan execution.

This hook runs BEFORE Bash commands that look like git commits.
It adds context reminding Claude of the commit protocol.
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
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""

def is_feature_branch(branch):
    """Check if branch is a feature branch off develop (not develop or main itself)."""
    if not branch or branch in ("develop", "main", "master", "HEAD"):
        return False
    # Feature branches: feature/*, fix/*, chore/*, or any branch that isn't develop/main
    # The key rule: NOT develop and NOT main = feature branch = auto-approve
    return True

def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # Can't parse, let it through

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only care about Bash commands
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # Check if this is a git commit command
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    # Check current branch - feature branches get auto-approved
    branch = get_current_branch()
    if is_feature_branch(branch):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": f"Auto-approved: commit on feature branch '{branch}'"
            }
        }
        print(json.dumps(output))
        return 0

    # On develop or main - full commit protocol required
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",  # Always ask for commits on develop/main
            "additionalContext": """
COMMIT PROTOCOL REMINDER (from CLAUDE.md):

Before this commit executes, verify:
1. Did you show `git status` to the user?
2. Did you show `git diff` to the user?
3. Did you show `git log -3` for message style?
4. Did you propose a commit message?
5. Did the user give EXPLICIT approval ("ok", "commit", "go ahead")?

If ANY of these are missing, STOP and complete them first.
A question from the user is NOT approval - answer it and wait again.
Note: Spec updates are checked at push time by spec_staleness_guard.py, not per-commit.
"""
        }
    }

    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
