#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: AC descope-drift guard.

Fires on `git commit` when staged files touch
docs/implementation-plans/<slug>/{test-requirements.md,phase_*.md}. For each
touched plan directory, runs claude-env's validate_ac_coverage.py (which
detects ACs marked DESCOPED in test-requirements.md but still referenced as
active in a sibling phase_*.md — see phase_04.md/AC4.2 for the real incident
this closes). Skips (never blocks) if claude-env isn't checked out at the
expected path.

Bypass: per-file <!-- AC-DESCOPE-OK: reason --> in the phase file (handled
inside validate_ac_coverage.py itself).
"""

import json
import os
import re
import subprocess
import sys
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _repo_context import enter_target_repo  # noqa: E402

PLAN_FILE_RE = re.compile(
    r'^docs/implementation-plans/([^/]+)/(test-requirements\.md|phase_\d+\.md)$'
)
VALIDATOR = os.path.expanduser(
    "~/projects/claude-env/helpers/validate_ac_coverage.py"
)


def _staged_files():
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.splitlines() if r.returncode == 0 else []
    except Exception:
        return []


def main():
    try:
        hook_input = json.load(sys.stdin)
        enter_target_repo(hook_input)
    except (json.JSONDecodeError, EOFError):
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    plan_dirs = set()
    for f in _staged_files():
        m = PLAN_FILE_RE.match(f)
        if m:
            plan_dirs.add(f"docs/implementation-plans/{m.group(1)}")

    if not plan_dirs:
        return 0
    if not os.path.isfile(VALIDATOR):
        return 0  # claude-env not present on this machine — skip, don't block

    failures = []
    for plan_dir in sorted(plan_dirs):
        r = subprocess.run(
            ["python3", VALIDATOR, plan_dir], capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            failures.append((plan_dir, r.stdout, r.stderr))

    if not failures:
        return 0

    print("\n[plan_ac_drift_guard] BLOCKED\n", file=sys.stderr)
    for plan_dir, out, err in failures:
        print(f"--- {plan_dir} ---", file=sys.stderr)
        print(out, file=sys.stderr)
        print(err, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
