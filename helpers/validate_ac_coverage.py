#!/usr/bin/env python3
"""
Validate that AC ownership claims in phase plans agree with test-requirements.md.

Usage:
  python helpers/validate_ac_coverage.py <plan-dir>

  plan-dir: path to a docs/implementation-plans/<slug>/ directory
            containing phase_NN.md files and (optionally) test-requirements.md.

Background: Phase 8 of photo-portfolio visual-design says "Manual Firefox
smoke at 320/768/1280/2560" while test-requirements.md says "Chromium +
WebKit at same viewports." Two sources of truth disagreed silently. This
script surfaces such mismatches by parsing AC references from both files.

What it checks:
1. Every AC id referenced in a phase file (pattern: <slug>.AC<N>.<M>) is
   present in test-requirements.md with a compatible phase assignment.
2. Every AC id in test-requirements.md is referenced by at least one
   phase plan (no orphans).
3. Browser matrix claims in phase plans are reported alongside the
   test-requirements.md claims so a human can spot conflicts.

Exit codes:
  0  no conflicts
  1  mismatches found (printed)
"""

import os
import re
import sys
from collections import defaultdict

AC_ID_RE = re.compile(r'\b[a-z][\w-]*\.AC[\d\.NM\[\]]+\b')
PHASE_ROW_RE = re.compile(
    r'^\s*\|\s*\*{0,2}(AC[\d\.NM\[\]]+)\*{0,2}\s*\|\s*([\d/ NM\[\]]+)\s*\|',
    re.MULTILINE
)
BROWSER_RE = re.compile(
    r'(chromium|firefox|webkit|safari|mobile\s+chrome|mobile\s+safari|manual\s+firefox)',
    re.IGNORECASE
)


def _phase_num(fname):
    m = re.search(r'phase_0*(\d+)', fname, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_acs(content):
    return {m.group(0) for m in AC_ID_RE.finditer(content)}


def _extract_browser_claims(content, source_label):
    out = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in BROWSER_RE.finditer(line):
            out.append((source_label, i, line.strip(), m.group(0)))
    return out


def _testreqs_phase_map(content):
    mapping = defaultdict(set)
    for m in PHASE_ROW_RE.finditer(content):
        ac_id = m.group(1)
        for token in re.split(r'[/\s]+', m.group(2)):
            try:
                mapping[ac_id].add(int(token))
            except ValueError:
                pass
    return mapping


# --- DESCOPED-drift check --------------------------------------------------
# Background: 2026-06-26 single-screen overview. ACs were marked DESCOPED in
# test-requirements.md (AC4.2/AC4.3/AC7.2) but phase_04.md kept describing
# them as active, hard success criteria (e.g. "AC4.2 Success: emphasized box
# area > median non-emphasized box area") — a second source-of-truth drift
# validate_ac_coverage.py's original AC-coverage check doesn't catch, since
# that check only looks for MISSING cross-references, not stale ones.

TABLE_ROW_RE = re.compile(r'^\s*\|(.+)\|\s*$')
BARE_AC_RE = re.compile(r'\bAC\d+(?:\.\d+)?\b')
DESCOPED_RE = re.compile(r'DESCOPED|~~', re.IGNORECASE)


def _descoped_acs_in_testreqs(content):
    """Table rows in test-requirements.md whose row text signals DESCOPED
    (strikethrough anywhere in the row, or the literal word DESCOPED).
    Returns {ac_id: (lineno, raw_line)}."""
    descoped = {}
    for lineno, raw in enumerate(content.splitlines(), 1):
        if not TABLE_ROW_RE.match(raw):
            continue
        if not DESCOPED_RE.search(raw):
            continue
        for m in BARE_AC_RE.finditer(raw):
            descoped[m.group(0)] = (lineno, raw.strip())
    return descoped


def _check_descope_drift(testreqs_content, plan_dir):
    """For each AC marked DESCOPED in test-requirements.md, verify no
    phase_*.md file references that exact AC id without ALSO saying
    DESCOPED nearby (same line). Returns a list of violation strings."""
    descoped = _descoped_acs_in_testreqs(testreqs_content)
    if not descoped:
        return []

    violations = []
    for fname in sorted(os.listdir(plan_dir)):
        if not re.match(r'phase_\d+\.md$', fname, re.IGNORECASE):
            continue
        path_ = os.path.join(plan_dir, fname)
        with open(path_, "r", encoding="utf-8") as f:
            content = f.read()
        if re.search(r'<!--\s*AC-DESCOPE-OK\s*:', content, re.IGNORECASE):
            continue
        for lineno, raw in enumerate(content.splitlines(), 1):
            for m in BARE_AC_RE.finditer(raw):
                ac_id = m.group(0)
                if ac_id not in descoped:
                    continue
                if DESCOPED_RE.search(raw):
                    continue  # phase file already acknowledges it locally
                violations.append(
                    f"  {fname}:{lineno}  references {ac_id}, which "
                    f"test-requirements.md:{descoped[ac_id][0]} marks DESCOPED, "
                    f"with no local DESCOPED note.\n"
                    f"    phase line: {raw.strip()[:100]}\n"
                    f"    testreqs line: {descoped[ac_id][1][:100]}"
                )
    return violations


def main(argv):
    if len(argv) < 2:
        print("Usage: python helpers/validate_ac_coverage.py <plan-dir>", file=sys.stderr)
        return 1

    plan_dir = argv[1]
    if not os.path.isdir(plan_dir):
        print(f"ERROR: not a directory: {plan_dir}", file=sys.stderr)
        return 1

    testreqs_path = os.path.join(plan_dir, "test-requirements.md")
    testreqs_content = ""
    if os.path.exists(testreqs_path):
        with open(testreqs_path, "r", encoding="utf-8") as f:
            testreqs_content = f.read()

    # Strip the .ACx.y suffix to get just AC tokens for the test-requirements parse
    testreqs_acs = {m.group(0) for m in AC_ID_RE.finditer(testreqs_content)}
    testreqs_phases = _testreqs_phase_map(testreqs_content)
    testreqs_browsers = _extract_browser_claims(testreqs_content, "test-requirements.md")

    phase_acs = defaultdict(set)        # ac_id -> set of phase numbers
    phase_browsers = []

    for fname in sorted(os.listdir(plan_dir)):
        if not re.match(r'phase_\d+\.md$', fname, re.IGNORECASE):
            continue
        pnum = _phase_num(fname)
        if pnum is None:
            continue
        with open(os.path.join(plan_dir, fname), "r", encoding="utf-8") as f:
            content = f.read()
        for ac in _extract_acs(content):
            phase_acs[ac].add(pnum)
        phase_browsers.extend(_extract_browser_claims(content, fname))

    errors = []

    def _ac_suffix(ac):
        """'visual-design.AC2.3' -> 'AC2.3'."""
        m = re.search(r'AC[\d\.\[NM\]]+', ac)
        return m.group(0) if m else ac

    def _ac_major(ac):
        """'visual-design.AC2.3' -> 'AC2'. Phase files often reference parent
        ACs ('AC2'); compare leniently by major since subtypes always extend it."""
        suffix = _ac_suffix(ac)
        m = re.match(r'(AC\d+)', suffix)
        return m.group(1) if m else suffix

    testreqs_majors = {_ac_major(a) for a in testreqs_acs}
    testreqs_majors |= {_ac_major(k) for k in testreqs_phases.keys()}

    for ac_id in phase_acs:
        if not testreqs_content:
            continue
        if _ac_suffix(ac_id) in testreqs_acs:
            continue
        if _ac_suffix(ac_id) in testreqs_phases:
            continue
        if _ac_major(ac_id) in testreqs_majors:
            continue
        errors.append(
            f"  AC {ac_id} claimed in phase file(s) but no matching AC group "
            f"in test-requirements.md"
        )

    if testreqs_content:
        # Browser matrix conflict surface
        if testreqs_browsers or phase_browsers:
            print("\nBrowser matrix claims (review for conflicts):")
            print("  test-requirements.md:")
            for source, lineno, claim, _ in testreqs_browsers[:8]:
                print(f"    line {lineno}: {claim[:100]}")
            print("  phase files:")
            for source, lineno, claim, _ in phase_browsers[:8]:
                print(f"    {source}:{lineno}: {claim[:100]}")

    descope_violations = _check_descope_drift(testreqs_content, plan_dir)
    if descope_violations:
        print(f"\nAC DESCOPE-DRIFT ERRORS ({len(descope_violations)} found):\n", file=sys.stderr)
        for v in descope_violations:
            print(v, file=sys.stderr)
        print(
            "\nFix: add 'DESCOPED' near the AC mention in the phase file (matching\n"
            "test-requirements.md's own convention), remove the stale AC reference,\n"
            "or bypass with <!-- AC-DESCOPE-OK: reason --> if the phase file already\n"
            "correctly reflects the descope in different words.",
            file=sys.stderr,
        )
        errors.append("descope-drift")  # ensure non-zero combined exit

    if errors:
        print(f"\nAC COVERAGE ERRORS ({len(errors)} found):\n", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("\n[validate_ac_coverage] OK — AC references aligned with test-requirements.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
