#!/usr/bin/env python3
"""
PreToolUse hook: block git commit when UI source files are staged
without recent Playwright verification.

Rules:
  - Triggers on any git commit command
  - Checks staged files for UI file extensions (.js, .ts, .tsx, .jsx,
    .css, .scss, .html, .svelte, .vue) or paths containing src/
  - Requires .playwright-ui-verified sentinel in repo root
  - Sentinel must exist AND be < 10 minutes old
  - If check fails: block with a clear message

Playwright scripts must write the sentinel on success:
    open('.playwright-ui-verified', 'w').close()
"""

import json
import os
import re
import subprocess
import sys
import time
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _repo_context import enter_target_repo  # noqa: E402

UI_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx", ".css", ".scss", ".html", ".svelte", ".vue"}
SENTINEL_NAME = ".playwright-ui-verified"
MAX_AGE_SECONDS = 600  # 10 minutes

COMMIT_RE = re.compile(r'\bgit\s+commit\b', re.IGNORECASE)


def block(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "block",
            "additionalContext": f"[playwright-gate] BLOCKED: {reason}"
        }
    }))
    sys.exit(0)


def allow():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)


def main():
    try:
        input_data = json.loads(sys.stdin.read())
        enter_target_repo(input_data)
    except Exception:
        allow()
        return

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if not COMMIT_RE.search(command):
        allow()
        return

    # Get repo root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        repo_root = result.stdout.strip()
        if not repo_root:
            allow()
            return
    except Exception:
        allow()
        return

    # Get staged files
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=repo_root
        )
        staged = result.stdout.strip().splitlines()
    except Exception:
        allow()
        return

    # Check if any staged file is a UI file
    ui_staged = []
    for f in staged:
        ext = os.path.splitext(f)[1].lower()
        if ext in UI_EXTENSIONS:
            ui_staged.append(f)

    if not ui_staged:
        allow()
        return

    # UI files staged — require sentinel
    sentinel_path = os.path.join(repo_root, SENTINEL_NAME)

    if not os.path.exists(sentinel_path):
        block(
            f"UI files staged ({', '.join(ui_staged[:3])}{'...' if len(ui_staged) > 3 else ''}) "
            f"but no Playwright verification found.\n"
            f"Run a Playwright test script first. "
            f"Scripts must write `{SENTINEL_NAME}` in the repo root on success."
        )
        return

    age = time.time() - os.path.getmtime(sentinel_path)
    if age > MAX_AGE_SECONDS:
        age_min = int(age / 60)
        block(
            f"UI files staged but Playwright verification is {age_min} minute(s) old "
            f"(max {MAX_AGE_SECONDS // 60} min).\n"
            f"Re-run a Playwright test to get fresh verification, then commit."
        )
        return

    allow()


if __name__ == "__main__":
    main()
