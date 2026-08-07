#!/usr/bin/env python3
"""Agent oversight: cap TaskOutput timeout to prevent indefinite blocking.

PreToolUse hook on TaskOutput tool. Ensures no TaskOutput call can block
the conversation for more than 60 seconds, even if the caller requests longer.

Reads tool_input from stdin JSON, returns updatedInput via stdout JSON.
Exit 0 = allow (with modifications). Never blocks.
"""

import json
import sys

MAX_TIMEOUT_MS = 60000


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        tool_input = input_data.get("tool_input", {})

        modified = False
        updated = dict(tool_input)

        # Cap timeout if over limit
        current_timeout = updated.get("timeout")
        if current_timeout is not None and current_timeout > MAX_TIMEOUT_MS:
            updated["timeout"] = MAX_TIMEOUT_MS
            modified = True

        # If blocking with no timeout set, add one
        if updated.get("block", True) and current_timeout is None:
            updated["timeout"] = MAX_TIMEOUT_MS
            modified = True

        if modified:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": updated,
                    "additionalContext": f"[agent-oversight] Capped TaskOutput timeout to {MAX_TIMEOUT_MS}ms."
                }
            }))
        else:
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
