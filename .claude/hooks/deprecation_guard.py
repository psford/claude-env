#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Flag deprecated API usage after dotnet builds.

After any `dotnet build` command, scans the build output for deprecation warnings
(CS0618, CS0612, SYSLIB*) and injects a reminder to fix them immediately.

Deprecation warnings are bugs, not noise — per CLAUDE.md's "Flag deprecated APIs" principle.
"""

import json
import sys
import re


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

    # Only care about dotnet build commands
    if not re.search(r'\bdotnet\b.*\bbuild\b', command, re.IGNORECASE):
        return 0

    # Check the tool output for deprecation warnings
    tool_output = hook_input.get("tool_output", "")
    if not tool_output:
        return 0

    # Match deprecation warning codes: CS0618 (Obsolete), CS0612 (Obsolete no message), SYSLIB*
    deprecation_pattern = r'warning (CS0618|CS0612|SYSLIB\d+)'
    matches = re.findall(deprecation_pattern, tool_output)

    if not matches:
        return 0

    # Count unique warning codes
    unique_codes = set(matches)
    total_count = len(matches)

    warning_list = ", ".join(sorted(unique_codes))

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"""
⚠️ DEPRECATION WARNINGS DETECTED ({total_count} warnings, codes: {warning_list})

Per CLAUDE.md "Flag deprecated APIs" principle:
- Investigate these warnings — don't ignore them
- Evaluate the migration path: what's the replacement API? Is it a simple swap or a structural change?
- If the fix is straightforward (e.g., SKPaint.TextSize → SKFont), fix it before committing
- If it's complex or risky, flag it for discussion with the user
- Common replacements:
  • SkiaSharp: Use SKFont instead of SKPaint.TextSize/Typeface/MeasureText
  • .NET SYSLIB*: Check Microsoft docs for the recommended replacement
"""
        }
    }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
