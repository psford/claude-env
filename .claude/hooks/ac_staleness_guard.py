#!/usr/bin/env python3
"""Advisory Claude Code hook (PostToolUse on Bash).

When a git push command is detected, checks ac-status.json for any ACs that are
stale (verified more than 30 days ago) or unverified. Prints an advisory warning
to stderr but always exits 0 (never blocks).
"""

import json
import os
import sys
from datetime import datetime, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATUS_FILE = os.path.join(REPO_ROOT, "infrastructure", "wsl", "ac-status.json")
STALE_DAYS = 30


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git push" not in command:
        sys.exit(0)

    if not os.path.exists(STATUS_FILE):
        sys.exit(0)

    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    criteria = data.get("criteria", {})
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)
    problem_count = 0

    for ac_id, ac in criteria.items():
        status = ac.get("status", "unverified")
        if status == "unverified":
            problem_count += 1
        elif status == "verified" and ac.get("verified_at"):
            try:
                verified_date = datetime.fromisoformat(ac["verified_at"])
                if verified_date < cutoff:
                    problem_count += 1
            except ValueError:
                pass

    if problem_count > 0:
        print(
            f"\u26a0 Advisory: {problem_count} acceptance criteria are unverified or stale\n"
            f"  Run: python infrastructure/wsl/ac-tracker.py stale",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
