#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: stderr suppression guard.

Blocks Bash commands that redirect stderr to /dev/null on substantive
commands (wsl, dotnet, apt, sudo, sed, tr, etc.). Safe uses like
existence checks (which, command -v, test -f) are allowed.

Add '# STDERR-SUPPRESS: reason' comment to intentionally suppress.
"""

import json
import sys
import re

SAFE_PATTERNS = re.compile(
    r'(?:'
    r'which\s+\w+|command\s+-v\s+\w+|type\s+\w+'
    r'|test\s+-[a-z]\s+'
    r'|\[\s*-[a-z]\s+'
    r'|\w+\s+--version'
    r'|grep\s+-q\b'
    r'|git\s+rev-parse\b'
    r'|git\s+show-ref\b'
    r')',
    re.IGNORECASE
)

RISKY_PATTERNS = re.compile(
    r'(?:'
    r'wsl\s+|dotnet\s+|apt(?:-get)?\s+|pip\s+|npm\s+'
    r'|curl\s+.*-o\s|wget\s+|sudo\s+|tee\s+'
    r'|sed\s+-i|tr\s+|az\s+|gh\s+|ssh\b'
    r')',
    re.IGNORECASE
)

SUPPRESS_RE = re.compile(r'2\s*>\s*/dev/null|2\s*>\s*NUL', re.IGNORECASE)
INTENTIONAL_RE = re.compile(r'#\s*STDERR-SUPPRESS\s*:', re.IGNORECASE)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if not command or not SUPPRESS_RE.search(command):
        return 0

    if INTENTIONAL_RE.search(command):
        return 0

    if SAFE_PATTERNS.search(command) and not RISKY_PATTERNS.search(command):
        return 0

    if RISKY_PATTERNS.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "block",
                "additionalContext": (
                    "BLOCKED: stderr suppression on substantive command.\n\n"
                    "Redirecting stderr to /dev/null hides error signals.\n"
                    "This is how a corrupted wsl.conf went undiagnosed for hours.\n\n"
                    "Options:\n"
                    "  1. Remove 2>/dev/null and let stderr surface\n"
                    "  2. Capture stderr: output=$(cmd 2>&1); echo \"$output\"\n"
                    "  3. Annotate: cmd 2>/dev/null  # STDERR-SUPPRESS: <reason>\n\n"
                    "Safe uses (existence checks, --version probes) are not blocked."
                )
            }
        }))
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
