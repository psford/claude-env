#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Fix-commit smell detector.

Fires after git commit. If the commit message starts with "fix:" and
the committed files overlap with the previous commit's files, emits
an advisory warning about the commit-before-test pattern.

Advisory only — adds context but does not block.
"""

import json
import sys
import re
import subprocess


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


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

    # Check if the most recent commit is a fix: commit
    last_msg = run_git("log", "-1", "--format=%s")
    if not last_msg or not last_msg.lower().startswith("fix:"):
        return 0

    # Get files changed in HEAD and HEAD~1
    head_files = set(run_git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    prev_files = set(run_git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD~1").splitlines())

    if not head_files or not prev_files:
        return 0

    # Filter out non-code files
    code_exts = {".py", ".cs", ".js", ".ts", ".sh", ".ps1"}
    head_code = {f for f in head_files if any(f.endswith(ext) for ext in code_exts)}
    prev_code = {f for f in prev_files if any(f.endswith(ext) for ext in code_exts)}

    overlap = head_code & prev_code
    if not overlap:
        return 0

    file_list = "\n".join(f"  - {f}" for f in sorted(overlap)[:5])
    suffix = f"\n  ... and {len(overlap) - 5} more" if len(overlap) > 5 else ""

    context = (
        f"FIX-COMMIT SMELL: This 'fix:' commit touches {len(overlap)} file(s) "
        f"also changed in the previous commit:\n{file_list}{suffix}\n\n"
        f"This pattern (commit then immediately fix) suggests the original commit "
        f"wasn't tested before committing. Consider:\n"
        f"  - Testing more thoroughly before committing\n"
        f"  - Squashing fix commits with their parent if still on a feature branch\n\n"
        f"This is advisory only — no action required if intentional."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
