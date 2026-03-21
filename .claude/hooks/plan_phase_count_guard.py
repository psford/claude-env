#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Implementation plan phase-count guard.

Fires on git commit. Detects when a new implementation plan directory
adds 5 or more phase_NN.md files. Plans with this many phases are
likely over-decomposed — making them rigid and inflating commit count.

Blocks commit (exit 2) unless first phase file contains:
  <!-- PHASES-JUSTIFIED: reason -->

Heuristic: 2-3 phases is correct for a JS+backend feature.
           4 is acceptable for cross-cutting changes.
           5+ requires explicit justification.
"""

import json
import sys
import re
import subprocess
from collections import defaultdict


PHASE_FILE_PATTERN = re.compile(
    r'docs/implementation-plans/([^/]+)/phase_\d+\.md$', re.IGNORECASE
)
JUSTIFICATION = re.compile(r'<!--\s*PHASES-JUSTIFIED\s*:', re.IGNORECASE)
PHASE_THRESHOLD = 5


def get_newly_added_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append(parts[1].replace("\\", "/"))
        return files
    except Exception:
        return []


def read_staged_content(filepath):
    try:
        result = subprocess.run(
            ["git", "show", f":{filepath}"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
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

    new_files = get_newly_added_files()
    if not new_files:
        return 0

    plans = defaultdict(list)
    for f in new_files:
        m = PHASE_FILE_PATTERN.search(f)
        if m:
            plans[m.group(1)].append(f)

    violations = []
    for plan_name, phase_files in plans.items():
        if len(phase_files) < PHASE_THRESHOLD:
            continue

        phase_files_sorted = sorted(phase_files)
        first_phase_content = read_staged_content(phase_files_sorted[0])
        if JUSTIFICATION.search(first_phase_content):
            continue

        violations.append({
            "plan": plan_name,
            "phase_count": len(phase_files),
            "files": phase_files_sorted
        })

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        f"BLOCKED: Implementation plan has {PHASE_THRESHOLD}+ phases — justify or consolidate",
        "=" * 70,
        "",
        "Plans with too many phases create rigid task lists before scope is understood.",
        "They inflate commit counts (6 phases = 18+ commits for a single feature).",
        "",
        "Heuristic:",
        "  2 phases — focused JS or backend feature",
        "  3 phases — JS + backend + persistence",
        "  4 phases — cross-cutting architectural changes",
        "  5+ phases — requires explicit justification",
        "",
    ]

    for v in violations:
        lines.append(f"Plan: {v['plan']}  ({v['phase_count']} phases)")
        for f in v["files"]:
            lines.append(f"  {f}")
        lines.append("")

    lines += [
        "REQUIRED — choose one:",
        "  1. Consolidate: combine UI + wiring, state + rendering into fewer phases.",
        "  2. Justify by adding to the first phase file:",
        "     <!-- PHASES-JUSTIFIED: reason -->",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
