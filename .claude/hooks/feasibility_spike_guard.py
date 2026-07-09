#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: feasibility / spike gate for design & implementation plans.

Background: 2026-06-26 single-screen overview. The design locked acceptance
criteria that depended on non-trivial MECHANISMS — "emphasized renders larger"
(a row-height boost surviving a fixed-height fill) and "lightbox navigates only
the shown subset" (PhotoSwipe tolerating rebind-while-open) — as HARD
requirements, with no spike to validate them first. Both proved false during
implementation and had to be descoped. This hook forces a feasibility section
when a plan makes mechanism claims.

What it does:
- Fires on `git commit` Bash invocations.
- Scans staged docs/design-plans/**.md and docs/implementation-plans/**.md.
- If a plan contains MECHANISM keywords (layout/interactive/animation/algorithmic
  claims) it must ALSO contain a `## Feasibility` / `## Spike(s)` / `## Proof of
  Concept` section, OR a phase named like "Spike:" / "PoC". Otherwise: BLOCK.
- Escape hatch: `<!-- SPIKE-EXEMPT: reason -->` anywhere in the file (use only for
  provably-simple CSS arithmetic with no library/browser-version dependency).

Exit: 0 allow, 2 block.
"""

import json
import re
import subprocess
import sys

PLAN_RE = re.compile(r"docs/(?:design-plans|implementation-plans)/.+\.md$", re.IGNORECASE)

MECHANISM = re.compile(
    r"\b("
    r"renders? larger|larger area|fit(?:s| to)?\s+(?:height|screen|viewport)"
    r"|fill(?:s)?\s+(?:the\s+)?(?:screen|viewport|height|width)"
    r"|binary.?search|row.?height|pixel.?exact|exact(?:ly)?\s+fill"
    r"|no(?:\s+)?(?:scroll|holes?|gaps?|crop)"
    r"|absolute.?position|resize.?observer|zoom\s+level"
    r"|lightbox|pswp|photoswipe|re.?bind|drag(?:gable)?|swipe|scroll.?lock"
    r"|animates?\s+back|transition(?:s)?\s+(?:to|from|when)"
    r"|converge[sd]?|within\s+tolerance"
    r")",
    re.IGNORECASE,
)

FEASIBILITY = re.compile(
    r"^#{2,4}\s+(?:Feasibility|Spikes?|Proof[\s-]of[\s-]Concept|PoC|Prototype)\b",
    re.IGNORECASE,
)
SPIKE_PHASE = re.compile(r"(?:^|\bPhase\b).*?\b(?:spike|poc|proof[\s-]of[\s-]concept|prototype)\b", re.IGNORECASE)
EXEMPT = re.compile(r"<!--\s*SPIKE-EXEMPT\s*:", re.IGNORECASE)


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _staged_plans():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"])
    return [f for f in out.splitlines() if PLAN_RE.search(f)] if rc == 0 else []


def _content(path):
    rc, out = _run(["git", "show", f":{path}"])
    return out if rc == 0 else ""


def _has_safeguard(text):
    return any(FEASIBILITY.match(ln.strip()) or SPIKE_PHASE.search(ln) for ln in text.splitlines())


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    if not re.search(r"\bgit\b.*\bcommit\b", data.get("tool_input", {}).get("command", ""), re.IGNORECASE):
        return 0

    offenders = []
    for path in _staged_plans():
        text = _content(path)
        if not text or EXEMPT.search(text):
            continue
        m = MECHANISM.search(text)
        if m and not _has_safeguard(text):
            offenders.append((path, m.group(0)))

    if not offenders:
        return 0

    print("\n[feasibility_spike_guard] BLOCKED", file=sys.stderr)
    print("Plan(s) make mechanism claims but have no ## Feasibility / ## Spike section:\n", file=sys.stderr)
    for path, kw in offenders:
        print(f"  {path}  (e.g. \"{kw}\")", file=sys.stderr)
    print(
        "\nFix one of:\n"
        "  - add a ## Feasibility section (what was validated + how), or\n"
        "  - add a ## Spikes section (PoC tasks with done-when), or\n"
        "  - name a phase 'Spike: ...' / 'PoC: ...'.\n"
        "Bypass (provably-simple CSS only): <!-- SPIKE-EXEMPT: reason -->\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
