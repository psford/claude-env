#!/usr/bin/env python3
"""
Pre-PR readiness check for phase plans.

Usage:
  python helpers/phase_pr_check.py <phase_NN.md> [--pr-body-file <file>]

Validates that a phase is actually ready to PR:
1. Every checkbox in the "Phase N Done When" section is [x] (not [ ])
2. Current branch is not main/master
3. If --pr-body-file is given, the PR body references the phase file
   or its plan directory (so reviewers can trace what's being shipped)

Designed to be called manually before `gh pr create`, or wired into a
post_push hook in claude-env's hook chain.

Exit codes:
  0  ready
  1  one or more readiness items failed
"""

import os
import re
import subprocess
import sys

DONE_WHEN_RE = re.compile(r'^##+\s+Phase\s+\d+\s+Done\s+When\b', re.IGNORECASE)
CHECKBOX_RE = re.compile(r'^\s*-\s*\[([ xX])\]\s+(.+)$')


def _current_branch():
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def _extract_unchecked(content):
    unchecked = []
    in_section = False
    for line in content.splitlines():
        if DONE_WHEN_RE.match(line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("#"):
            break
        if in_section:
            m = CHECKBOX_RE.match(line)
            if m and m.group(1) == " ":
                unchecked.append(m.group(2).strip())
    return unchecked


def main(argv):
    if len(argv) < 2:
        print("Usage: python helpers/phase_pr_check.py <phase_NN.md> [--pr-body-file <file>]",
              file=sys.stderr)
        return 1

    phase_path = argv[1]
    if not os.path.exists(phase_path):
        print(f"ERROR: phase file not found: {phase_path}", file=sys.stderr)
        return 1

    pr_body_path = None
    if "--pr-body-file" in argv:
        idx = argv.index("--pr-body-file")
        if idx + 1 < len(argv):
            pr_body_path = argv[idx + 1]

    with open(phase_path, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []
    unchecked = _extract_unchecked(content)
    if unchecked:
        errors.append("Unchecked 'Phase N Done When' items:")
        for item in unchecked:
            errors.append(f"    - [ ] {item}")

    branch = _current_branch()
    if branch in ("main", "master"):
        errors.append(f"Current branch is '{branch}' — PRs must come from a feature branch.")

    if pr_body_path and os.path.exists(pr_body_path):
        with open(pr_body_path, "r", encoding="utf-8") as f:
            body = f.read()
        slug = os.path.basename(phase_path)
        parent = os.path.basename(os.path.dirname(phase_path))
        if slug not in body and parent not in body:
            errors.append(f"PR body does not reference phase file '{slug}' or plan dir '{parent}'.")

    if errors:
        print(f"\nPR READINESS CHECK FAILED for {os.path.basename(phase_path)}\n",
              file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"[phase_pr_check] OK — {os.path.basename(phase_path)} on branch '{branch}'")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
