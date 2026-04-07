#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Commit claim verification guard.

Advisory hook (exit 0 with additionalContext — never blocks).

When a git commit message contains verification claims such as:
  "tests pass", "working", "verified", "confirmed", "visible", etc.

...injects context requiring Claude to show actual test output or
command output before the commit proceeds.

This combats the "assert without verify" pattern where Claude states
a feature works without running a command that proves it.

Exit codes:
  0 = always (advisory only — uses additionalContext, not stderr blocking)
"""

import json
import re
import sys


# Claims that imply verification has occurred
CLAIM_PATTERNS = [
    re.compile(r'\btests?\s+pass(?:es|ing)?\b', re.IGNORECASE),
    re.compile(r'\ball\s+tests?\b', re.IGNORECASE),
    re.compile(r'\bworking\b', re.IGNORECASE),
    re.compile(r'\bverified?\b', re.IGNORECASE),
    re.compile(r'\bconfirmed?\b', re.IGNORECASE),
    re.compile(r'\bvisible\b', re.IGNORECASE),
    re.compile(r'\bsuccessfully\b', re.IGNORECASE),
    re.compile(r'\bnow\s+works?\b', re.IGNORECASE),
    re.compile(r'\bfixed\b', re.IGNORECASE),
    re.compile(r'\bpassing\b', re.IGNORECASE),
    re.compile(r'\bgreen\b', re.IGNORECASE),
    re.compile(r'\bvalidated?\b', re.IGNORECASE),
    re.compile(r'\bfunctional\b', re.IGNORECASE),
    re.compile(r'\boperational\b', re.IGNORECASE),
]


def extract_commit_message(command):
    """
    Extract the -m message value from a git commit command string.
    Handles: -m "...", -m '...', heredoc (<<'EOF'), and plain -m word.
    Returns the message string or None if not extractable.
    """
    # HEREDOC: cat <<'EOF'\n...\nEOF — extract the body
    heredoc_match = re.search(
        r"<<['\"]?(\w+)['\"]?\n(.*?)\n\1",
        command,
        re.DOTALL
    )
    if heredoc_match:
        return heredoc_match.group(2)

    # -m "..." or -m '...'
    quoted_match = re.search(
        r'-m\s+(["\'])(.*?)\1',
        command,
        re.DOTALL
    )
    if quoted_match:
        return quoted_match.group(2)

    # -m word (unquoted single token)
    plain_match = re.search(r'-m\s+(\S+)', command)
    if plain_match:
        return plain_match.group(1)

    return None


def find_claims(message):
    """Return list of matched claim strings found in the message."""
    found = []
    for pattern in CLAIM_PATTERNS:
        m = pattern.search(message)
        if m:
            found.append(m.group(0))
    return found


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    message = extract_commit_message(command)
    if not message:
        return 0

    claims = find_claims(message)
    if not claims:
        return 0

    claim_list = ", ".join(f'"{c}"' for c in claims)

    context = (
        f"COMMIT-CLAIM VERIFICATION REQUIRED\n\n"
        f"The commit message contains verification claim(s): {claim_list}\n\n"
        f"CLAUDE.md rule: NEVER say 'X works' or 'Y is visible' without running a "
        f"command that proves it first.\n\n"
        f"REQUIRED before this commit lands:\n"
        f"  1. Run the relevant tests and paste the actual output.\n"
        f"     Example: dotnet test --filter Category=Unit\n"
        f"     Example: npm test\n"
        f"     Example: python -m pytest tests/\n"
        f"  2. If the claim is visual (\"visible\", \"rendered\"), open the page and "
        f"describe what you see — or share a curl/fetch that returns the expected data.\n"
        f"  3. If the claim cannot be verified in this session, REMOVE it from the "
        f"commit message and note the limitation.\n\n"
        f"Paste the command output here, then Patrick will approve the commit."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
