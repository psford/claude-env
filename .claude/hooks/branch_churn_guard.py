#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: branch churn / thrash advisory (NEVER blocks).

Background: 2026-06-26. Approaches tried-then-abandoned within a branch (a commit
adds code a later commit deletes) are a forensic signal of thrash. This surfaces
that after a commit, as a nudge. It is ADVISORY ONLY (exit 0) — refactors and
normal iteration produce the same pattern, so the false-positive rate is high.
The real control for "stop freelancing" is the pass/fail contract; this is just
visibility. Lowest-value of the retro mitigations.

Signals (advisory):
- COMMIT COUNT: branch has > COMMIT_WARN commits vs the base branch.
- FILE REVERSAL: a file's net lines gained on the branch dropped > REVERSAL of its
  peak in a later commit.

Exit: always 0.
"""

import json
import re
import subprocess
import sys

COMMIT_WARN = 8
REVERSAL = 0.6
BASES = ["origin/main", "origin/develop", "main", "develop"]


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    if not re.search(r"\bgit\b.*\bcommit\b", data.get("tool_input", {}).get("command", ""), re.IGNORECASE):
        return 0

    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch or branch in ("HEAD", "main", "develop"):
        return 0
    base = next((b for b in BASES if _run(["git", "rev-parse", "--verify", b])[0] == 0), "")
    if not base:
        return 0
    rc, out = _run(["git", "log", "--format=%H", f"{base}..HEAD"])
    if rc != 0 or not out:
        return 0
    shas = list(reversed(out.splitlines()))

    notes = []
    if len(shas) > COMMIT_WARN:
        notes.append(
            f"{branch} has {len(shas)} commits vs {base} (> {COMMIT_WARN}). "
            "If it's iterating without converging, reconsider the approach before adding more."
        )

    net, peak = {}, {}
    for sha in shas:
        rc, out = _run(["git", "diff-tree", "--no-commit-id", "-r", "--numstat", sha])
        if rc != 0:
            continue
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            a, d, path = parts
            try:
                a, d = int(a), int(d)
            except ValueError:
                continue
            net[path] = net.get(path, 0) + a - d
            if net[path] > peak.get(path, 0):
                peak[path] = net[path]
            elif peak.get(path, 0) > 10 and d > 0 and (peak[path] - net[path]) / peak[path] >= REVERSAL:
                notes.append(
                    f"{path}: gained {peak[path]} lines on this branch then lost "
                    f"{round((peak[path]-net[path])/peak[path]*100)}% (commit {sha[:8]}) — "
                    "an approach may have been tried then abandoned."
                )

    if not notes:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "[branch_churn_guard] ADVISORY (weak signal, high false-positive — "
                "refactors look the same):\n  " + "\n  ".join(notes)
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
