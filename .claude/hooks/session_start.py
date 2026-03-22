#!/usr/bin/env python3
"""
Claude Code SessionStart hook: Load critical context at session start.

Outputs checkpoint reminders, open retro mitigations, and claudeLog staleness.
"""

import json
import sys
import os
import re
from datetime import datetime, date


RETRO_MITIGATIONS_PATH = "docs/retrospectives/2026-03-22-wsl2-sandbox-retro-mitigations.md"
CLAUDELOG_PATH = "claudeLog.md"
CLAUDELOG_STALE_DAYS = 7
# Optional: Set SPECS_PATH env var to customize which spec files to check
SPECS_PATH = os.environ.get("SPECS_PATH", "")  # Empty string = no spec checking

COMPLETED_RE = re.compile(r'^\s*-\s*\[x\]', re.IGNORECASE)
DATE_HEADING_RE = re.compile(r'^##\s+(\d{2}/\d{2}/\d{4})')


def load_open_mitigations(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []

    completed_nums = set()
    for line in content.split("\n"):
        if COMPLETED_RE.match(line):
            m = re.search(r'#(\d+)', line)
            if m:
                completed_nums.add(m.group(1))

    open_items = []
    for line in content.split("\n"):
        m = re.match(r'^###\s+(#\d+\s+.+?)\s*\(', line)
        if m:
            title = m.group(1).strip()
            num_match = re.match(r'#(\d+)', title)
            if num_match and num_match.group(1) not in completed_nums:
                open_items.append(title)

    return open_items


def get_claudelog_staleness_days(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None

    latest = None
    for line in lines:
        m = DATE_HEADING_RE.match(line.strip())
        if m:
            try:
                entry_date = datetime.strptime(m.group(1), "%m/%d/%Y").date()
                if latest is None or entry_date > latest:
                    latest = entry_date
            except ValueError:
                continue

    if latest is None:
        return None
    return (date.today() - latest).days


def main():
    checkpoints = """\
=== CRITICAL CHECKPOINTS (enforced by hooks) ===

COMMITS: Show status -> diff -> log -> message -> WAIT for explicit approval
MAIN BRANCH: Never commit, merge, push --force, or rebase on main
REVERSE MERGE: Never merge main INTO develop (flow is develop -> main)
PR MERGE: Patrick merges via GitHub web only - never use `gh pr merge`
DEPLOY: Only when Patrick says "deploy" + pre-deploy checklist complete
"""
    # Only show SPECS checkpoint if specs are configured for this repo
    if SPECS_PATH:
        checkpoints += f"SPECS: Update {SPECS_PATH} AS you code, stage with code\n"

    checkpoints += """\
QUESTIONS: If user asks a question, answer and wait - not implicit approval

These rules are enforced by Claude Code hooks. Violations will be blocked.
"""

    warnings = []

    open_items = load_open_mitigations(RETRO_MITIGATIONS_PATH)
    if open_items:
        item_lines = "\n".join(f"  - {item}" for item in open_items[:3])
        suffix = f" (showing first 3 of {len(open_items)})" if len(open_items) > 3 else ""
        warnings.append(
            f"OPEN RETRO MITIGATIONS: {len(open_items)} unimplemented{suffix}\n"
            f"{item_lines}\n"
            f"Full list: {RETRO_MITIGATIONS_PATH}"
        )

    stale_days = get_claudelog_staleness_days(CLAUDELOG_PATH)
    if stale_days is not None and stale_days >= CLAUDELOG_STALE_DAYS:
        warnings.append(
            f"CLAUDELOG STALE: Last entry is {stale_days} days old (limit: {CLAUDELOG_STALE_DAYS}).\n"
            f"Update {CLAUDELOG_PATH} before ending this session."
        )

    output = checkpoints
    if warnings:
        output += "\n=== SESSION WARNINGS ===\n\n"
        output += "\n\n".join(warnings)
        output += "\n"

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
