#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: plan / decisions.md descope-drift guard.

Background: 2026-06-26. When ACs were descoped mid-implementation, the reversal
was recorded in docs/decisions.md but the plan's Definition of Done / Acceptance
Criteria still listed them as active hard requirements — false done-criteria, no
re-sign-off. This catches that drift.

What it does:
- Fires on `git commit` Bash invocations.
- Reads docs/decisions.md (staged if staged, else on disk) for AC ids marked
  DESCOPED/DEFERRED (an AC id like `slug.AC4.2` within 3 lines of the marker).
- For each staged plan .md (docs/**.md except decisions.md), flags any of those
  AC ids that still appear UNannotated (no strike ~~..~~, no DESCOPED/DEFERRED,
  no `<!-- DRIFT-OK: -->`). BLOCK if found.

Exit: 0 allow, 2 block.
"""

import json
import re
import subprocess
import sys

DECISIONS = "docs/decisions.md"
PLAN_RE = re.compile(r"^docs/.+\.md$", re.IGNORECASE)
AC_ID = re.compile(r"\b([\w][\w-]*\.AC\d+(?:\.\d+)?)\b")
DESCOPE = re.compile(r"\b(?:DESCOPED|DEFERRED|DESCOPE|DROPPED|REMOVED)\b", re.IGNORECASE)
ANNOTATED = re.compile(r"~~|DESCOPED|DEFERRED|DROPPED|REMOVED|<!--\s*DRIFT-OK\s*:", re.IGNORECASE)


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _staged():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"])
    return out.splitlines() if rc == 0 else []


def _staged_content(path):
    rc, out = _run(["git", "show", f":{path}"])
    return out if rc == 0 else ""


def _disk(path):
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
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    if not re.search(r"\bgit\b.*\bcommit\b", data.get("tool_input", {}).get("command", ""), re.IGNORECASE):
        return 0

    staged = _staged()
    plans = [f for f in staged if PLAN_RE.search(f) and f != DECISIONS]
    if not plans:
        return 0

    decisions = _staged_content(DECISIONS) if DECISIONS in staged else _disk(DECISIONS)
    descoped = _descoped_ids(decisions) if decisions else set()
    if not descoped:
        return 0

    offenders = []
    for path in plans:
        for n, ln in enumerate(_staged_content(path).splitlines(), 1):
            if ANNOTATED.search(ln):
                continue
            for m in AC_ID.finditer(ln):
                if m.group(1).upper() in descoped:
                    offenders.append((path, n, m.group(1)))

    if not offenders:
        return 0

    print("\n[plan_descope_drift_guard] BLOCKED", file=sys.stderr)
    print("AC(s) marked DESCOPED/DEFERRED in decisions.md are still active in plan(s):\n", file=sys.stderr)
    for path, n, ac in offenders:
        print(f"  {path}:{n}  {ac}", file=sys.stderr)
    print(
        "\nFix: strike (~~AC~~), annotate (DESCOPED — see decisions.md), or delete the AC in the plan.\n"
        "If the AC is actually still active, correct decisions.md first.\n"
        "Bypass: append <!-- DRIFT-OK: reason --> to the AC line.\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
