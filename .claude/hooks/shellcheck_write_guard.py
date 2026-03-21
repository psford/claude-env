#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Bash syntax guard for .sh file writes.

Fires on Write tool targeting .sh files. Runs `bash -n` on the content
to catch syntax errors before the file is written.

Blocks write (exit 2) on syntax error.
"""

import json
import sys
import subprocess
import tempfile
import os


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Write":
        return 0

    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".sh"):
        return 0

    content = tool_input.get("content", "")
    if not content:
        return 0

    # Write content to a temp file and run bash -n
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = subprocess.run(
            ["bash", "-n", tmp_path],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            errors = result.stderr.strip()
            lines = [
                "",
                "=" * 70,
                f"BLOCKED: Bash syntax error in {file_path}",
                "=" * 70,
                "",
                errors,
                "",
                "Fix the syntax errors before writing.",
                "=" * 70,
            ]
            print("\n".join(lines), file=sys.stderr)
            return 2

    except subprocess.TimeoutExpired:
        pass  # Don't block on timeout
    except FileNotFoundError:
        pass  # bash not available, skip check
    finally:
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
