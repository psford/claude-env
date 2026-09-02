#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: a visual acceptance criterion must be manual.

Patrick, 2026-09-02, on a hobby tool that had grown 1,688 lines of test
against 1,883 lines of production code, and on my own admission that not
one real defect that session had been caught by a test:

    "NOT A SINGLE ISSUE FOUND"
    "The token incineration machine is back, baby!"

Then, on my writing the lesson into a markdown rule:

    "how will that actual bite? you have shown that you will ignore
     ANYTHING written in an MD file"

He is right, and this hook is the answer. The shared rule ("Test what you
can't see; look at what you can") has no teeth on its own. This gives it
teeth at the exact point the damage starts.

WHY THE ROOT CAUSE IS THE CRITERION, NOT THE TEST
-------------------------------------------------
Every `automated` acceptance criterion demands a `verified_by`, and the
mechanical gate refuses the ticket without one. So the moment an analyst
writes "the page shows X" as an AUTOMATED criterion, a rendering test
becomes mandatory -- and a rendering test asserts that a template emitted
what the template says. It can only fail when someone edits the template,
at which point the fix is to update the test. It catches nothing.

The test bloat was downstream of the criterion. Blocking the criterion is
therefore the only place a block does real work; blocking the test would
just deadlock a ticket whose AC still demands one.

WHAT IT DOES
------------
Fires on Bash invocations of `ticket ac add`. If the criterion's text
describes something a person SEES -- renders, displays, shows, is visible,
the page contains, a label, a theme, a layout -- and the call does not
pass `--kind manual`, it exits 2 and says to add `--kind manual`.

Visual criteria are not banned. They are routed to Patrick's eyes, which
found every real defect the session this hook came from.

ZERO TRUST
----------
There is NO escape hatch: no env var, no magic comment, no token an agent
can type (shared rules, "Zero trust -- TNO"). If a criterion is genuinely
about machine-checkable structure rather than appearance, WORD IT THAT WAY
-- describe the observable state, not what it looks like. If that is
impossible, it is a visual criterion and it belongs to Patrick.
"""

import json
import re
import shlex
import sys

# Words that mean "a person looked at it". Deliberately about APPEARANCE,
# not about structure: "returns", "exits", "writes", "contains the key"
# are all machine-checkable and stay automated.
VISUAL_PATTERNS = [
    r"\brenders?\b", r"\brendering\b", r"\bdisplays?\b", r"\bshows?\b",
    r"\bvisible\b", r"\bvisually\b", r"\blooks?\b", r"\breads? as\b",
    r"\bappears?\b", r"\bon screen\b", r"\bthe page contains\b",
    r"\blabel(l?ed|s)?\b", r"\btheme\b", r"\bdark mode\b", r"\blight mode\b",
    r"\blayout\b", r"\bstyl(e|ed|ing)\b", r"\bcolou?r\b", r"\bfont\b",
    r"\bscroll(s|ing|bar)?\b", r"\bviewport\b", r"\bresponsive\b",
    r"\bin firefox\b", r"\bin chrome\b", r"\bin safari\b",
    r"\bscreenshot\b", r"\bui\b", r"\bpage reads\b",
]

_TICKET_AC_ADD = re.compile(r"\bticket\b[^|;&]*\bac\b\s+add\b")


def _segments(command):
    """Split a compound shell command into candidate invocations."""
    return re.split(r"&&|\|\||;|\n", command)


def _parse(segment):
    """(text, kind) for a `ticket ac add` segment, or (None, None)."""
    try:
        parts = shlex.split(segment)
    except ValueError:
        # Unbalanced quotes: cannot parse, so cannot judge. Fail OPEN here
        # rather than block an unrelated command -- the ticket CLI itself
        # will reject a malformed call.
        return None, None
    text = kind = None
    for i, p in enumerate(parts):
        if p == "--text" and i + 1 < len(parts):
            text = parts[i + 1]
        elif p.startswith("--text="):
            text = p.split("=", 1)[1]
        elif p == "--kind" and i + 1 < len(parts):
            kind = parts[i + 1]
        elif p.startswith("--kind="):
            kind = p.split("=", 1)[1]
    return text, kind


def _visual_hits(text):
    lowered = text.lower()
    return [p for p in VISUAL_PATTERNS if re.search(p, lowered)]


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = hook_input.get("tool_input", {}).get("command", "") or ""
    if "ticket" not in command or " ac " not in f" {command} ":
        return 0

    offences = []
    for segment in _segments(command):
        if not _TICKET_AC_ADD.search(segment):
            continue
        text, kind = _parse(segment)
        if not text or (kind or "").strip().lower() == "manual":
            continue
        hits = _visual_hits(text)
        if hits:
            offences.append((text, hits))

    if not offences:
        return 0

    print(
        "\n[visual_ac_manual_guard] BLOCKED: a visual acceptance criterion "
        "must be --kind manual.\n",
        file=sys.stderr,
    )
    for text, hits in offences:
        words = ", ".join(h.strip("\\b").replace("\\b", "") for h in hits[:4])
        print(f"  criterion: {text[:110]}", file=sys.stderr)
        print(f"  reads as visual because of: {words}\n", file=sys.stderr)
    print(
        "An automated AC demands a verified_by, so this criterion would force a\n"
        "rendering test -- and a rendering test asserts a template emitted what\n"
        "the template says. It fails only when someone edits the template, and\n"
        "then the fix is to update the test. It catches nothing.\n\n"
        "Two ways forward:\n"
        "  - it IS about appearance -> add --kind manual, and Patrick judges it\n"
        "  - it is NOT -> reword it as observable state rather than appearance\n"
        "    (\"the manifest carries a stale flag\", not \"the page shows stale\")\n\n"
        "There is no override. Patrick, 2026-09-02: not one real defect that\n"
        "session was caught by a test; every one was caught by looking.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
