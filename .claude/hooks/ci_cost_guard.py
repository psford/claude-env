#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: CI cost guard.

Background: 2026-07-08 — a Claude instance submitted three needless iOS
builds to GitHub Actions within minutes, exhausting Patrick's entire
monthly Actions quota (macOS runners bill at a 10x minute multiplier).
Patrick's standing rulings (2026-07-09, both permanent):
  - FINAL WARNING: a repeat means the subscription is cancelled.
  - "you're never allowed to use github to test ios again."

What this hook does (Bash commands only):
1. Workflow-dispatch class — `gh workflow run`, `gh run rerun`,
   `gh api ...dispatches`:
   - If the repo's .github/workflows contains ANY macOS runner:
     UNCONDITIONAL BLOCK. No bypass token exists on purpose — this is
     the permanent iOS-on-GitHub ban. iOS builds run locally (Mac
     xcodebuild / the local CI runner).
   - Otherwise: BLOCK unless CI_RUN_OK=1 (explicit, per-command human
     ack that a metered remote run is intended).
2. `git push` to a repo whose .github/workflows uses macOS runners:
   BLOCK unless CI_MACOS_PUSH_OK=1 — a push *triggers* those workflows,
   so shipping code to an iOS repo requires Patrick's explicit ack of
   the minute spend. Pushes to repos with only Linux runners (or no
   workflows) pass silently: normal development friction stays zero.

Detection is deliberately conservative: any `runs-on:` line mentioning
macos, in any workflow file, marks the repo as macOS-billing. False
positives cost one env-var ack; false negatives cost the subscription.
"""

import json
import os
import re
import subprocess
import sys

DISPATCH_RE = re.compile(
    r'\bgh\s+workflow\s+run\b|\bgh\s+run\s+rerun\b|\bgh\s+api\b[^|;&]*dispatches',
    re.IGNORECASE,
)
PUSH_RE = re.compile(r'\bgit\b[^|;&]*\bpush\b')
MACOS_RUNNER_RE = re.compile(r'runs-on\s*:.*mac[oO][sS]|runs-on\s*:.*\bmacos-', re.IGNORECASE)


def _repo_root(cwd):
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _workflow_files(repo_root):
    wf_dir = os.path.join(repo_root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return []
    return [
        os.path.join(wf_dir, f)
        for f in os.listdir(wf_dir)
        if f.endswith((".yml", ".yaml"))
    ]


def _has_macos_runner(repo_root):
    for path in _workflow_files(repo_root):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                if MACOS_RUNNER_RE.search(f.read()):
                    return True
        except OSError:
            continue
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0

    is_dispatch = bool(DISPATCH_RE.search(command))
    is_push = bool(PUSH_RE.search(command))
    if not (is_dispatch or is_push):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    repo_root = _repo_root(cwd)
    if repo_root is None:
        return 0
    has_workflows = bool(_workflow_files(repo_root))
    macos = _has_macos_runner(repo_root)

    if is_dispatch:
        if macos:
            print(
                "\n[ci_cost_guard] BLOCKED — PERMANENTLY.\n"
                "This repo's workflows use macOS runners (10x minute billing), and\n"
                "Patrick's standing ruling (2026-07-09) is: GitHub is never used to\n"
                "test iOS again. There is deliberately NO bypass for this.\n\n"
                "Run iOS builds/tests locally: xcodebuild on the Mac, or the local\n"
                "CI runner (see feedback_metered_ci_discipline memory for status).",
                file=sys.stderr,
            )
            return 2
        if has_workflows and os.environ.get("CI_RUN_OK") != "1":
            print(
                "\n[ci_cost_guard] BLOCKED.\n"
                "This command triggers a remote GitHub Actions run — metered minutes.\n"
                "A Claude instance exhausted the entire monthly quota on 2026-07-08;\n"
                "remote CI runs now require explicit human acknowledgment.\n\n"
                "Validate locally first. If the remote run is genuinely intended and\n"
                "Patrick has approved the spend:  CI_RUN_OK=1 <command>",
                file=sys.stderr,
            )
            return 2
        return 0

    # git push path
    if macos and os.environ.get("CI_MACOS_PUSH_OK") != "1":
        print(
            "\n[ci_cost_guard] BLOCKED.\n"
            "This repo has workflows on macOS runners (10x minute billing) that a\n"
            "push can trigger. Pushing here requires Patrick's explicit ack of the\n"
            "minute spend (permanent policy after the 2026-07-08 quota exhaustion):\n\n"
            "  CI_MACOS_PUSH_OK=1 git push ...\n\n"
            "iOS build/test themselves are permanently banned from GitHub — run\n"
            "them locally (xcodebuild / the local CI runner).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
