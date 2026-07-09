#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: simplest-path annotation guard for implementation phases.

Background: 2026-06-26. A CSS-level task ("make one photo a bit bigger") was solved
with a pixel-exact binary-search fill solver — massively over-engineered. The plan
never recorded the simpler approach considered. This forces an explicit
"Simplest path considered:" note on any AC group that claims a non-trivial
mechanism, so the altitude is chosen deliberately.

What it does:
- Fires on `git commit` Bash invocations.
- Scans staged docs/implementation-plans/**/phase_*.md.
- For each `### slug.ACn` group containing a MECHANISM keyword, requires a
  "Simplest path considered:" (or "Simplest path:") line in the group. BLOCK if missing.
- Bypass per AC group: `<!-- SIMPLEST-PATH-OK: reason -->` on the AC header line.

Exit: 0 allow, 2 block.
"""

import json
import re
import subprocess
import sys

PHASE_RE = re.compile(r"docs/implementation-plans/.+/phase_\d+\.md$", re.IGNORECASE)
AC_HEADER = re.compile(r"^###\s+[\w][\w-]*\.AC\d+", re.IGNORECASE)
NEXT_HEADER = re.compile(r"^#{1,3}\s")
MECHANISM = re.compile(
    r"\b("
    r"renders? larger|larger area|fit(?:s| to)?\s+(?:height|screen|viewport)"
    r"|fill(?:s)?\s+(?:the\s+)?(?:screen|viewport|height|width)"
    r"|binary.?search|row.?height|pixel.?exact|exact(?:ly)?\s+fill"
    r"|no(?:\s+)?(?:scroll|holes?|gaps?|crop)|absolute.?position|resize.?observer"
    r"|lightbox|pswp|photoswipe|re.?bind|drag(?:gable)?|scroll.?lock"
    r"|animates?\s+back|transition(?:s)?\s+(?:to|from)|converge[sd]?|within\s+tolerance"
    r")",
    re.IGNORECASE,
)
SIMPLEST = re.compile(r"simplest[\s-]?path", re.IGNORECASE)
OK = re.compile(r"<!--\s*SIMPLEST-PATH-OK\s*:", re.IGNORECASE)


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _staged_phases():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"])
    return [f for f in out.splitlines() if PHASE_RE.search(f)] if rc == 0 else []


def _content(path):
    rc, out = _run(["git", "show", f":{path}"])
    return out if rc == 0 else ""


def _violations(text):
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if AC_HEADER.match(lines[i].strip()):
            header = lines[i]
            j = i + 1
            body = []
            while j < len(lines) and not NEXT_HEADER.match(lines[j]):
                body.append(lines[j])
                j += 1
            group = header + "\n" + "\n".join(body)
            if not OK.search(header) and MECHANISM.search(group) and not any(SIMPLEST.search(b) for b in body):
                out.append((i + 1, header.strip()))
            i = j
        else:
            i += 1
    return out


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
    for path in _staged_phases():
        for n, header in _violations(_content(path)):
            offenders.append((path, n, header))

    if not offenders:
        return 0

    print("\n[simplest_path_guard] BLOCKED", file=sys.stderr)
    print("AC group(s) with mechanism claims lack a 'Simplest path considered:' note:\n", file=sys.stderr)
    for path, n, header in offenders:
        print(f"  {path}:{n}  {header[:80]}", file=sys.stderr)
    print(
        "\nFix: add a bullet to each AC group:\n"
        "  - **Simplest path considered:** <lowest-complexity approach + why chosen/rejected>\n"
        "If this IS the simplest path: say 'simplest known path: <reason>'.\n"
        "Bypass: append <!-- SIMPLEST-PATH-OK: reason --> to the AC header line.\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
