#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Retrospective trigger.

Fires after git commit. Detects two signals that indicate a retrospective
entry should be logged:

  1. REVERT: Commit message starts with "revert" or contains "revert:"
  2. MULTI-ATTEMPT: The same source file appears in 3+ of the last 10 commits

When detected, injects a MANDATORY context block requiring a retro entry
be written to .claude/retrospective-log.md before the next commit.

Advisory output (no exit code 2) — injects into response as hard context.
"""

import json
import sys
import re
import subprocess
from collections import Counter
from datetime import datetime


REVERT_PATTERN = re.compile(r'^\s*revert\b|revert\s*:', re.IGNORECASE)
MULTI_ATTEMPT_THRESHOLD = 3
RECENT_COMMITS_WINDOW = 10


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_last_commit_message():
    return run_git("log", "-1", "--pretty=%s")


def get_files_in_recent_commits(n):
    output = run_git("log", f"-{n}", "--name-only", "--pretty=format:")
    if not output:
        return []
    return [line.strip() for line in output.split("\n") if line.strip()]


def get_current_branch():
    return run_git("rev-parse", "--abbrev-ref", "HEAD")


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

    branch = get_current_branch()
    if not branch or branch == "main":
        return 0

    last_message = get_last_commit_message()
    triggers = []

    # Signal 1: Revert commit
    if REVERT_PATTERN.search(last_message):
        triggers.append({
            "type": "revert",
            "detail": f'Commit message: "{last_message}"'
        })

    # Signal 2: Multi-attempt (same source file in 3+ of last 10 commits)
    if not triggers:
        recent_files = get_files_in_recent_commits(RECENT_COMMITS_WINDOW)
        counts = Counter(recent_files)
        hot_files = [
            (f, n) for f, n in counts.most_common(5)
            if n >= MULTI_ATTEMPT_THRESHOLD
            and not f.endswith(".md")
            and "node_modules" not in f
            and ".claude" not in f
        ]
        if hot_files:
            triggers.append({
                "type": "multi_attempt",
                "detail": ", ".join(f"{f} ({n}x)" for f, n in hot_files[:3])
            })

    if not triggers:
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    trigger_descriptions = []
    for t in triggers:
        if t["type"] == "revert":
            trigger_descriptions.append(f"REVERT detected: {t['detail']}")
        elif t["type"] == "multi_attempt":
            trigger_descriptions.append(f"MULTI-ATTEMPT detected: {t['detail']}")

    context = (
        f"RETROSPECTIVE ENTRY REQUIRED\n\n"
        f"Trigger(s):\n"
        + "\n".join(f"  - {d}" for d in trigger_descriptions) +
        f"\n\nThis signals something didn't go right the first time. "
        f"The retrospective-log.md exists precisely for this.\n\n"
        f"BEFORE the next commit, write an entry to:\n"
        f"  .claude/retrospective-log.md\n\n"
        f"Entry format:\n"
        f"  ## {today}: [short title]\n"
        f"  **Category:** Dead end / Plan failure / Unexpected complexity / Config friction\n"
        f"  **Time wasted:** ~X minutes\n"
        f"  **What happened:** [what went wrong and why]\n"
        f"  **Fix:** [what actually worked]\n"
        f"  **Critical lesson:** [the rule or pattern to add to CLAUDE.md]\n\n"
        f"The log is at .claude/retrospective-log.md. Be specific."
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
