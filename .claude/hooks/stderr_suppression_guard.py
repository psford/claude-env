#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: stderr suppression guard.

Blocks Bash commands that redirect stderr to /dev/null on substantive
commands (wsl, dotnet, apt, sudo, sed, tr, etc.). Safe uses like
existence checks (which, command -v, test -f) are allowed.

Add '# STDERR-SUPPRESS: reason' comment to intentionally suppress.
"""

import json
import os
import sys
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _repo_context import QUOTED, strip_heredoc_bodies  # noqa: E402


def shell_shaped(command):
    """The parts of a command where `2>/dev/null` would be a real redirect.

    Deliberately NOT scannable_text. That keeps an interpreter's `-c` body
    intact, because a python one-liner genuinely is code -- correct for guards
    about what a command DOES. This guard is about a shell redirect, and inside
    `python3 -c "..."` a `2>/dev/null` is almost always a string, not a
    redirect. Two false blocks inside five minutes of activation, both on
    tooling that suppressed nothing.

    The residual gap, stated: a one-liner that shells out with suppression
    (`subprocess.run("wsl.exe ... 2>/dev/null", shell=True)`) is now missed.
    That is a deliberate trade -- a guard that fires on every python heredoc is
    a guard that gets switched off, and then it catches nothing at all.
    """
    stripped = strip_heredoc_bodies(command, scan_interpreter_bodies=False)
    return QUOTED.sub(lambda m: " " * len(m.group()), stripped)

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
    # `.exe` is not optional decoration here: inside WSL, `wsl` is NOT a
    # command -- `wsl.exe` is the only spelling that exists. The pattern
    # `wsl\s+` could therefore never match a real invocation, so the guard's
    # headline case had been dead since it was written. Verified 2026-08-09
    # with `which wsl` (nothing) against `wsl.exe --status 2>/dev/null`
    # (passed straight through). The same applies to the other binaries that
    # are commonly reached across the boundary.
    r'wsl(?:\.exe)?\s+|dotnet(?:\.exe)?\s+|apt(?:-get)?\s+|pip\s+|npm(?:\.cmd)?\s+'
    r'|curl\s+.*-o\s|wget\s+|sudo\s+|tee\s+'
    r'|sed\s+-i|tr\s+|az(?:\.cmd)?\s+|gh(?:\.exe)?\s+|ssh\b'
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

    # Instructions only, not quoted data. Caught within minutes of this guard
    # being activated on 2026-08-09: a Python source string containing
    # `tr a b 2>/dev/null` was blocked, as was a heredoc writing a fixture.
    # Neither was running anything. scannable_text (not just heredoc-stripping)
    # is right here because the SHAPE of the command is the subject -- a
    # suppression quoted inside an argument is text, not a redirect.
    command = shell_shaped(command)

    if not command or not SUPPRESS_RE.search(command):
        return 0

    if INTENTIONAL_RE.search(command):
        return 0

    if SAFE_PATTERNS.search(command) and not RISKY_PATTERNS.search(command):
        return 0

    if RISKY_PATTERNS.search(command):
        # To STDERR, not only stdout. Exiting 2 is what blocks, and the harness
        # surfaces stderr for a blocking hook -- so a reason printed solely as
        # stdout JSON is a block with no explanation. Observed on 2026-08-09,
        # minutes after activation: "No stderr output" and nothing else, on a
        # command that should never have been refused.
        print(
            "BLOCKED: stderr suppression on a substantive command.\n"
            "  Redirecting stderr to /dev/null hides the error you need.\n"
            "  Remove it, capture with 2>&1, or annotate:  # STDERR-SUPPRESS: <reason>",
            file=sys.stderr,
        )
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
