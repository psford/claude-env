#!/usr/bin/env python3
"""
Claude Code SessionStart hook: Plan-staleness scan.

Closes the one gap plan_descope_drift_guard.py (PreToolUse/git-commit)
can't: that hook only checks plan files that are STAGED in the same
commit as a docs/decisions.md DESCOPED/DEFERRED entry. If a plan is
descoped and never touched again in any later commit, the drift guard
never fires. This scan runs at session start, reads decisions.md +
every plan file ON DISK (not just staged), and prints (does not edit)
any still-active, unannotated AC references. Advisory only — exit 0
always.
"""

import glob
import os
import re
import sys

DECISIONS = "docs/decisions.md"
PLAN_GLOB = "docs/implementation-plans/**/*.md"
AC_ID = re.compile(r"\b([\w][\w-]*\.AC\d+(?:\.\d+)?)\b")
DESCOPE = re.compile(r"\b(?:DESCOPED|DEFERRED|DESCOPE|DROPPED|REMOVED)\b", re.IGNORECASE)
ANNOTATED = re.compile(r"~~|DESCOPED|DEFERRED|DROPPED|REMOVED|<!--\s*DRIFT-OK\s*:", re.IGNORECASE)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _descoped_ids(text):
    ids, lines = set(), text.splitlines()
    for i, ln in enumerate(lines):
        if DESCOPE.search(ln):
            window = "\n".join(lines[max(0, i - 3):i + 4])
            ids.update(m.group(1).upper() for m in AC_ID.finditer(window))
    return ids


def main():
    if not os.path.exists(DECISIONS):
        return 0
    descoped = _descoped_ids(_read(DECISIONS))
    if not descoped:
        return 0

    offenders = []
    for path in glob.glob(PLAN_GLOB, recursive=True):
        for n, ln in enumerate(_read(path).splitlines(), 1):
            if ANNOTATED.search(ln):
                continue
            for m in AC_ID.finditer(ln):
                if m.group(1).upper() in descoped:
                    offenders.append((path, n, m.group(1)))

    if not offenders:
        return 0

    print("=== PLAN STALENESS: descoped AC(s) still active in plan files ===\n")
    for path, n, ac in offenders[:15]:
        print(f"  {path}:{n}  {ac}")
    if len(offenders) > 15:
        print(f"  ... and {len(offenders) - 15} more")
    print(
        "\ndocs/decisions.md marks the above AC(s) DESCOPED/DEFERRED, but the "
        "plan file still\nlists them as active. Strike (~~AC~~) or annotate "
        "them next time you touch the plan.\n"
        "(Advisory only — plan_descope_drift_guard.py already blocks this at "
        "commit time when\nthe plan file itself is staged.)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
