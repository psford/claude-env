#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block deferred items that lack Owner + Due date.

Background: across multiple retrospectives, items marked as "deferred" or
"future" without a concrete owner or date became permanent backlog
sediment — visual design, QA matrix, Phase 7 hardening, "stage 2 (TBD)".
The original failure was a Markdown "Deferred Items" table accepting
rows like "| Visual design | | later |". The hook closed that.

2026-06-11 expansion (Patrick caught a second case): the hook only
matched `## Deferred Items` / `## Backlog` h2 headers and only enforced
TABLE rows. Design plans use other phrasings — `## Out of scope`,
`**Out of scope:**` inline-bold markers — and often use BULLET LISTS
instead of tables. Both gaps let me ship a Section-5 bullet list with
no owners or dates earlier this session, exactly the pattern the hook
was supposed to prevent.

What this hook does now:
- Fires on `git commit` Bash invocations.
- Scans staged Markdown files for a deferred/out-of-scope section,
  recognized either as:
    * an h2-h4 header matching one of:
        "Deferred Items", "Backlog", "Out of scope", "Out-of-scope",
        "Future work", "Follow-on(s)", "TODO"
    * a bolded inline marker matching the same phrases (e.g.
        `**Out of scope:**` or `**Deferred:**`) on its own line
- Inside such sections, BOTH table rows AND bullet items must declare
  Owner and Due (YYYY-MM-DD).
    * For tables: existing column logic (header row → owner_col, due_col).
    * For bullets: require inline `Owner: <name>` and `Due: <YYYY-MM-DD>`
      OR an "n/a" pair (for items that are not actually deferred —
      "n/a / n/a" + a "Not deferred" prefix or similar marker).
- Blocks (exit 2) on any violation.
- Escape hatches:
    * Per-row: `<!-- DEFER-PERMANENT: reason -->` (intentionally
      permanent — e.g. won't-fix, out-of-scope forever).
    * Bullet-form bullets that are explicitly tagged "n/a" for both
      Owner and Due pass through (interpreted as "not actually deferred,
      just listed for context").
"""

import json
import re
import subprocess
import sys

PLAN_RE = re.compile(r'\.md$', re.IGNORECASE)

# Section labels that trigger enforcement, whether as h2-h4 header or
# bolded inline marker.
SECTION_KEYWORDS = (
    "Deferred Items",
    "Backlog",
    "Out of scope",
    "Out-of-scope",
    "Future work",
    "Follow-ons",
    "Follow-on",
    "TODO",
    "Deferred",
)
_KEYWORD_ALT = "|".join(re.escape(k) for k in SECTION_KEYWORDS)
HEADER_RE = re.compile(rf'^#{{2,4}}\s+({_KEYWORD_ALT})\b', re.IGNORECASE)
# Bolded inline marker on its own line, e.g. "**Out of scope:**" or
# "**Out of scope (with notes):**". The colon is optional.
INLINE_MARKER_RE = re.compile(
    rf'^\s*\*\*\s*({_KEYWORD_ALT})\b[^*]*\*\*\s*:?\s*$',
    re.IGNORECASE,
)

TABLE_ROW_RE = re.compile(r'^\s*\|(.+)\|\s*$')
# A bullet: -, *, +, or 1., 2., etc. Captures everything after the marker.
BULLET_RE = re.compile(r'^\s*(?:[-*+]|\d+\.)\s+(.+)$')

DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
PERMANENT_ESCAPE = re.compile(r'<!--\s*DEFER-PERMANENT\s*:', re.IGNORECASE)
EMPTY_OWNERS = {"", "-", "—", "tbd", "?", "n/a"}

# Inline Owner/Due markers in bullet form. Accept variants:
#   "Owner: Patrick", "owner: me",  "(Owner: Patrick)", "owner=Patrick".
INLINE_OWNER_RE = re.compile(r'\bowner\s*[:=]\s*([^,;|()\n]+)', re.IGNORECASE)
INLINE_DUE_RE = re.compile(r'\bdue\s*[:=]\s*([^,;|()\n]+)', re.IGNORECASE)


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


def _is_table_separator(cells):
    return all(re.match(r'^[-:\s]+$', c) for c in cells if c)


def _check_table_row(path, lineno, raw, owner_col, due_col, violations):
    cells = [c.strip() for c in raw.strip().strip("|").split("|")]
    if _is_table_separator(cells):
        return
    if PERMANENT_ESCAPE.search(raw):
        return
    item_desc = cells[0] if cells else raw.strip()
    if owner_col is None or due_col is None:
        violations.append((path, lineno, item_desc,
                           "table missing Owner or Due header column"))
        return
    owner_val = cells[owner_col].lower() if owner_col < len(cells) else ""
    due_val = cells[due_col] if due_col < len(cells) else ""
    # "n/a" in both Owner and Due is the explicit "not actually deferred,
    # just listed for context" pattern.
    if owner_val == "n/a" and due_val.strip().lower() == "n/a":
        return
    if owner_val in EMPTY_OWNERS:
        violations.append((path, lineno, item_desc, "missing Owner"))
    if not DATE_RE.search(due_val):
        violations.append((path, lineno, item_desc,
                           "missing Due date (YYYY-MM-DD)"))


def _check_bullet(path, lineno, raw, violations):
    if PERMANENT_ESCAPE.search(raw):
        return
    m = BULLET_RE.match(raw)
    if not m:
        return
    body = m.group(1)
    item_desc = body.strip()[:80]
    owner_m = INLINE_OWNER_RE.search(body)
    due_m = INLINE_DUE_RE.search(body)
    owner_val = owner_m.group(1).strip().lower() if owner_m else ""
    due_val = due_m.group(1).strip() if due_m else ""
    # Explicit "n/a" pair → not actually deferred, just contextual.
    if owner_val == "n/a" and due_val.lower() == "n/a":
        return
    if not owner_m or owner_val in EMPTY_OWNERS:
        violations.append((path, lineno, item_desc, "bullet missing Owner"))
    if not due_m or not DATE_RE.search(due_val):
        violations.append((path, lineno, item_desc,
                           "bullet missing Due date (YYYY-MM-DD)"))


def _check_file(path, content):
    violations = []
    in_section = False
    header_seen = False
    owner_col = due_col = None
    blank_run = 0  # Inline-marker sections end after 2 consecutive blank lines.
    marker_section = False  # True when triggered by INLINE_MARKER_RE.

    for lineno, raw in enumerate(content.splitlines(), 1):
        stripped = raw.strip()

        # Section entry: header (h2-h4) or inline bold marker.
        if HEADER_RE.match(stripped):
            in_section = True
            marker_section = False
            header_seen = False
            owner_col = due_col = None
            blank_run = 0
            continue
        if INLINE_MARKER_RE.match(raw):
            in_section = True
            marker_section = True
            header_seen = False
            owner_col = due_col = None
            blank_run = 0
            continue

        # Section exit:
        #  - Any h1-h4 header (in_section=False).
        #  - For inline-marker sections, two consecutive blank lines.
        if in_section and raw.startswith("#"):
            in_section = False
            continue
        if not in_section:
            continue
        if marker_section:
            if stripped == "":
                blank_run += 1
                if blank_run >= 2:
                    in_section = False
                continue
            else:
                blank_run = 0

        # Inside section: tables and bullets are both enforced.
        if TABLE_ROW_RE.match(raw):
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if not header_seen:
                lower = [c.lower() for c in cells]
                if "owner" in lower:
                    owner_col = lower.index("owner")
                if "due" in lower:
                    due_col = lower.index("due")
                header_seen = True
                continue
            _check_table_row(path, lineno, raw, owner_col, due_col, violations)
            continue

        if BULLET_RE.match(raw):
            _check_bullet(path, lineno, raw, violations)
            continue

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
