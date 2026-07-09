#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Design sign-off gate.

Background: photo-portfolio's emphasis feature burned ~30h across three
implementation attempts, each of which shipped visual-surface code before
a design was approved:
  - Attempt 1/2 (2026-06-26): docs/design-plans/2026-06-26-overview-single-screen.md
    was marked "<!-- DRAFT -- pending Patrick's sign-off before implementation -->"
    and the implementation plan executed anyway, on the exact assumption
    (row-height emphasis boost) that implementation later disproved.
  - Attempt 3 (2026-07-08): no design doc existed at all. Problem statement
    to full code to rejection, same session.

What this hook does:
- Fires on `git commit` Bash invocations, ONLY when the current branch
  starts with `feat/`.
- If the commit stages no visual-surface files, allow.
- Otherwise requires at least one docs/design-plans/*.md file (tracked or
  staged) that contains an explicit, non-placeholder Sign-off/Approved
  line. Design docs are matched to the branch by filename-word overlap;
  if no design doc's filename overlaps, ALL tracked design docs are
  considered candidates.
- Blocks (exit 2) if:
    (a) zero design-plan docs exist in the repo at all, or
    (b) none of the candidate docs contain a Sign-off/Approved line.
- Escape hatch: <!-- DESIGN-SIGNOFF-OK: reason --> anywhere in the
  git commit command (message body).
"""

import json
import os
import re
import subprocess
import sys

VISUAL_SURFACE_RE = re.compile(
    r'^(src/(site|pages|layouts|styles)/.*\.(astro|css|ts|tsx)$|.*\.astro$|.*\.css$)'
)
DESIGN_PLAN_RE = re.compile(r'^docs/design-plans/.+\.md$')
SIGNOFF_RE = re.compile(r'\*{0,2}\s*(Sign-?off|Approved)\s*\*{0,2}\s*:\s*(.+)', re.IGNORECASE)
DRAFT_RE = re.compile(r'\bDRAFT\b', re.IGNORECASE)
PLACEHOLDER_VALUE_RE = re.compile(r'^\s*(\[.*\]|TBD|N/A|_+)\s*$', re.IGNORECASE)
ESCAPE_RE = re.compile(r'<!--\s*DESIGN-SIGNOFF-OK\s*:', re.IGNORECASE)
STOPWORDS = {"the", "and", "for", "with", "screen", "single", "design", "docs", "plan", "plans"}


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def _current_branch():
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out if rc == 0 else ""


def _staged_files():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return out.splitlines() if rc == 0 else []


def _all_design_docs():
    rc, out = _run(["git", "ls-files", "docs/design-plans/"])
    tracked = set(out.splitlines()) if rc == 0 else set()
    staged = {f for f in _staged_files() if DESIGN_PLAN_RE.match(f)}
    return sorted(tracked | staged)


def _content_of(path):
    rc, out = _run(["git", "show", f":{path}"])
    if rc == 0 and out:
        return out
    rc, out = _run(["git", "show", f"HEAD:{path}"])
    return out if rc == 0 else ""


def _slug_words(s):
    return {w for w in re.findall(r'[a-z0-9]+', s.lower()) if len(w) >= 4} - STOPWORDS


def _is_signed_off(content):
    for line in content.splitlines():
        m = SIGNOFF_RE.search(line)
        if m and not PLACEHOLDER_VALUE_RE.match(m.group(2)):
            return True
    return False


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
    if ESCAPE_RE.search(command):
        return 0

    branch = _current_branch()
    if not branch.startswith("feat/"):
        return 0

    staged = _staged_files()
    visual_files = [f for f in staged if VISUAL_SURFACE_RE.match(f)]
    if not visual_files:
        return 0

    design_docs = _all_design_docs()
    if not design_docs:
        print(
            "\n[design_signoff_guard] BLOCKED\n"
            f"Branch '{branch}' is committing visual-surface changes "
            f"({len(visual_files)} file(s): {', '.join(visual_files[:5])}"
            f"{'...' if len(visual_files) > 5 else ''})\n"
            "but NO docs/design-plans/*.md exists anywhere in the repo.\n\n"
            "This is the attempt-3 pattern: problem statement -> code, no design doc,\n"
            "rejected on first visual review. Write a design doc first.\n\n"
            "Bypass (trivial CSS/copy nit only): include\n"
            "  <!-- DESIGN-SIGNOFF-OK: reason -->\nin the commit message.",
            file=sys.stderr
        )
        return 2

    branch_words = _slug_words(branch[len("feat/"):])
    candidates = [
        d for d in design_docs if branch_words & _slug_words(os.path.basename(d))
    ] or design_docs

    signed = []
    unsigned = []
    for d in candidates:
        content = _content_of(d)
        if _is_signed_off(content):
            signed.append(d)
        else:
            unsigned.append((d, bool(DRAFT_RE.search(content))))

    if signed:
        return 0

    print(
        "\n[design_signoff_guard] BLOCKED\n"
        f"Branch '{branch}' is committing visual-surface changes but no candidate\n"
        "design doc has an explicit Sign-off/Approved line.\n\n"
        "Candidate design doc(s) checked:",
        file=sys.stderr
    )
    for d, is_draft in unsigned:
        tag = " [marked DRAFT]" if is_draft else ""
        print(f"  {d}{tag}", file=sys.stderr)
    print(
        "\nThis is the attempt-2 pattern: a DRAFT design doc's unproven assumption\n"
        "shipped anyway. Add a line like:\n"
        "  **Sign-off:** Patrick approved <what> on <date>.\n"
        "to the design doc before committing implementation.\n\n"
        "Bypass (trivial CSS/copy nit only): include\n"
        "  <!-- DESIGN-SIGNOFF-OK: reason -->\nin the commit message.",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
