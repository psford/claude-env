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

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _repo_context import target_data_file  # noqa: E402

# CH-58. This was REPO_ROOT = dirname(__file__)/../.. , which is claude-env
# whichever repo the push is from -- so a push out of photo-portfolio was judged
# against claude-env's acceptance-criteria status. The file now comes from the
# repo being pushed, and its absence means dormant.
STATUS_RELATIVE = ("infrastructure", "wsl", "ac-status.json")
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

    status_file = target_data_file(hook_input, *STATUS_RELATIVE)
    if not status_file:
        sys.exit(0)

    try:
        with open(status_file, "r") as f:
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
