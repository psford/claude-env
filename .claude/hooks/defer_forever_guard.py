#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block deferred items that lack Owner + Due date.

Background: across multiple retrospectives, items marked as "deferred" or
"future" without a concrete owner or date became permanent backlog
sediment — visual design, QA matrix, Phase 7 hardening, "stage 2 (TBD)".
The pattern is that a Markdown "Deferred Items" or "Backlog" table accepts
rows like "| Visual design | | later |" and nothing forces them to grow
into "| Visual design | Patrick | 2026-09-01 |".

What this hook does:
- Fires on `git commit` Bash invocations.
- Scans staged Markdown files for any section header matching
  `## Deferred Items` or `## Backlog` (case-insensitive).
- Reads the table immediately under each such header. Identifies the
  Owner and Due columns from the header row.
- Blocks (exit 2) if any data row is missing either a non-empty Owner cell
  or a Due cell containing a YYYY-MM-DD date.
- Escape hatch: a `<!-- DEFER-PERMANENT: reason -->` comment on the same
  row marks an intentionally permanent deferral (out-of-scope item that
  will never be done in this project).
"""

import json
import re
import subprocess
import sys

PLAN_RE = re.compile(r'\.md$', re.IGNORECASE)
SECTION_RE = re.compile(r'^##+\s+(Deferred Items|Backlog)\b', re.IGNORECASE)
TABLE_ROW_RE = re.compile(r'^\s*\|(.+)\|\s*$')
DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
PERMANENT_ESCAPE = re.compile(r'<!--\s*DEFER-PERMANENT\s*:', re.IGNORECASE)
EMPTY_OWNERS = {"", "-", "—", "tbd", "?", "n/a"}


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _staged_md_files():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"])
    if rc != 0:
        return []
    return [f for f in out.strip().splitlines() if PLAN_RE.search(f)]


def _staged_content(path):
    rc, out = _run(["git", "show", f":{path}"])
    return out if rc == 0 else ""


def _check_file(path, content):
    violations = []
    in_section = False
    header_seen = False
    owner_col = due_col = None

    for lineno, raw in enumerate(content.splitlines(), 1):
        if SECTION_RE.match(raw.strip()):
            in_section = True
            header_seen = False
            owner_col = due_col = None
            continue
        if in_section and raw.startswith("#"):
            in_section = False
            continue
        if not in_section:
            continue

        if not TABLE_ROW_RE.match(raw):
            continue

        cells = [c.strip() for c in raw.strip().strip("|").split("|")]

        if not header_seen:
            lower = [c.lower() for c in cells]
            if "owner" in lower:
                owner_col = lower.index("owner")
            if "due" in lower:
                due_col = lower.index("due")
            header_seen = True
            continue

        # Separator row
        if all(re.match(r'^[-:\s]+$', c) for c in cells if c):
            continue

        if PERMANENT_ESCAPE.search(raw):
            continue

        item_desc = cells[0] if cells else raw.strip()
        if owner_col is None or due_col is None:
            # Table doesn't declare Owner/Due columns — surface that.
            violations.append((path, lineno, item_desc,
                               "table missing Owner or Due header column"))
            # Don't continue scanning this row's cells.
            continue

        owner_val = cells[owner_col].lower() if owner_col < len(cells) else ""
        due_val = cells[due_col] if due_col < len(cells) else ""

        if owner_val in EMPTY_OWNERS:
            violations.append((path, lineno, item_desc, "missing Owner"))
        if not DATE_RE.search(due_val):
            violations.append((path, lineno, item_desc,
                               "missing Due date (YYYY-MM-DD)"))

    return violations


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    files = _staged_md_files()
    if not files:
        return 0

    all_violations = []
    for path in files:
        all_violations.extend(_check_file(path, _staged_content(path)))

    if not all_violations:
        return 0

    print(
        "\n[defer_forever_guard] BLOCKED\n"
        "Deferred items must have Owner + Due date (YYYY-MM-DD).\n",
        file=sys.stderr
    )
    for path, lineno, item, reason in all_violations:
        print(f"  {path}:{lineno}  [{reason}]  item: {item[:80]}", file=sys.stderr)
    print(
        "\nFix: fill in Owner and Due (YYYY-MM-DD), or mark out-of-scope with:\n"
        "     <!-- DEFER-PERMANENT: reason -->",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
