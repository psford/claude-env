#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Spec staleness guard.

Fires after git push. Compares source-code delta on this branch against the
project's technical spec. If significant source changes exist but the spec
has not been touched in this branch, injects a reminder.

Spec path resolution (first match wins):
  1. $SPEC_STALENESS_PATH environment variable (explicit override; path is
     relative to the repo root)
  2. Convention: docs/TECHNICAL_SPEC.md, TECHNICAL_SPEC.md, docs/technical-spec.md,
     docs/spec.md, or SPEC.md in the current repo

If no spec is found by either mechanism, the check is skipped cleanly
(useful for standalone repos without a spec file — e.g., claude-env itself).

Advisory only (no exit 2) — injects into the response as hard context.
Replaces the per-commit spec reminder in git_commit_guard.py.

Threshold: 50 net changed lines of .js/.cs/.ts/.py code without any spec change.
"""

import json
import sys
import re
import subprocess
import os


SOURCE_EXTENSIONS = re.compile(r'\.(js|cs|ts|py)$', re.IGNORECASE)
# Paths that are NOT application source — don't require spec updates
EXCLUDED_PATHS = re.compile(
    r'^(?:'
    r'\.claude/|'
    r'infrastructure/|'
    r'docs/|'
    r'helpers/hooks/|'
    r'projects/hook-test/|'
    r'\.github/'
    r')'
)
# Convention-based spec paths, checked in order. Relative to repo root.
CONVENTION_SPEC_PATHS = (
    "docs/TECHNICAL_SPEC.md",
    "TECHNICAL_SPEC.md",
    "docs/technical-spec.md",
    "docs/spec.md",
    "SPEC.md",
)
NEW_LINES_THRESHOLD = 50


def resolve_spec_path():
    """Return the spec path relative to repo root, or None if none exists.

    Order: $SPEC_STALENESS_PATH env var, then convention paths.
    """
    env_path = os.environ.get("SPEC_STALENESS_PATH")
    repo_root = run_git("rev-parse", "--show-toplevel")
    if not repo_root:
        return None

    if env_path:
        # Env var wins even if the file is missing — surface the misconfig
        # to the caller rather than silently falling through to convention.
        return env_path

    for candidate in CONVENTION_SPEC_PATHS:
        if os.path.isfile(os.path.join(repo_root, candidate)):
            return candidate

    return None


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_merge_base():
    return run_git("merge-base", "HEAD", "origin/main")


def get_spec_diff_lines(merge_base, spec_path):
    if not merge_base or not spec_path:
        return 0
    diff = run_git("diff", merge_base, "HEAD", "--", spec_path)
    if not diff:
        return 0
    added = sum(1 for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++"))
    return added


def get_source_diff_lines(merge_base):
    if not merge_base:
        return 0
    diff = run_git("diff", merge_base, "HEAD", "--stat")
    if not diff:
        return 0

    total = 0
    for line in diff.split("\n"):
        m = re.match(r'\s*(.+?)\s*\|\s*(\d+)', line)
        if not m:
            continue
        fpath, changes = m.group(1).strip(), int(m.group(2))
        if SOURCE_EXTENSIONS.search(fpath) and not EXCLUDED_PATHS.match(fpath):
            total += changes
    return total


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
    if not re.search(r'\bgit\b.*\bpush\b', command, re.IGNORECASE):
        return 0

    # Resolve spec path after we know this is actually a push — avoids
    # running git in every Bash call. Skip cleanly if no spec file exists
    # (standalone repos like claude-env itself).
    spec_path = resolve_spec_path()
    if not spec_path:
        return 0

    branch = get_current_branch()
    if not branch or branch in ("main", "develop"):
        return 0

    run_git("fetch", "origin", "main", "--quiet", timeout=15)

    merge_base = get_merge_base()
    if not merge_base:
        return 0

    source_lines = get_source_diff_lines(merge_base)
    spec_lines = get_spec_diff_lines(merge_base, spec_path)

    if spec_lines > 0 or source_lines < NEW_LINES_THRESHOLD:
        return 0

    context = (
        f"SPEC STALENESS WARNING\n\n"
        f"Branch '{branch}' has {source_lines} changed lines of source code "
        f"since branching from main, but {spec_path} has 0 changes.\n\n"
        f"CLAUDE.md requires: Update {spec_path} AS you code, "
        f"stage with code commits.\n\n"
        f"Before this push is complete:\n"
        f"1. Read {spec_path}\n"
        f"2. Add/update sections covering: architecture changes, new endpoints, "
        f"new JS modules, changed data flows\n"
        f"3. Stage and commit the spec update\n"
        f"4. Push again\n\n"
        f"If the changes are genuinely non-spec-worthy (CSS tweaks, test files only), "
        f"add a comment in the commit message explaining why."
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
