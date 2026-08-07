#!/usr/bin/env python3
"""Commit gate: force user approval before any git commit executes.

PreToolUse hook on Bash tool. Detects git commit commands and returns
"ask" permission decision, which forces Claude Code's permission prompt.
The user must click approve before the command runs.

This exists because Claude cannot be trusted to follow the commit
protocol (show message, wait for approval) through prompting alone.
"""

import json
import re
import sys


# Patterns that indicate a git commit command
COMMIT_PATTERNS = [
    r'\bgit\s+commit\b',
    r'\bgit\s+.*\bcommit\b',
]


def is_git_commit(command: str) -> bool:
    """Check if a bash command contains a git commit."""
    for pattern in COMMIT_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if is_git_commit(command):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "additionalContext": (
                        "[commit-gate] git commit detected. "
                        "Review the commit message and approve or deny."
                    )
                }
            }))
        else:
            # Not a commit — allow without interference
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow"
                }
            }))

    except Exception:
        # Never break the system — allow and move on
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }))


if __name__ == "__main__":
    main()
