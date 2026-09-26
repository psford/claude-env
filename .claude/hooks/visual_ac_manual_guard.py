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

SHOWS, SEE, LOOK, DISPLAY -- WORDS, NOT VERDICTS (CE-2.38)
------------------------------------------------------------
"Reading vite.config.ts shows vitest's default excludes kept, not replaced"
was refused as visual for the word "shows" -- an everyday verb, used here to
report what a file's contents are, not what a person watched happen on a
rendered page. A handful of words (shows, sees, looks, displays) are used
constantly for both: reading a file, a command's output, an exit code or a
named test AND watching something appear on screen. Refusing on the word
alone punishes the first sense to catch the second.

So those four words are judged, not banned outright: they only block when
the criterion does not also name a checkable thing it is judging -- a file,
a command, an exit code, or a test (see ANCHOR_PATTERNS). Every OTHER visual
word (renders, theme, layout, viewport, "on screen", ...) still blocks
unconditionally -- those describe appearance and nothing else, so there is
no everyday sense to protect. A criterion about what someone sees on a
rendered page keeps blocking: it names no file, command, exit code or test,
so the everyday-word exemption never applies to it.

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

# Words that mean ONLY "a person looked at it" -- there is no everyday,
# machine-checkable sense to protect, so these block unconditionally.
# Deliberately about APPEARANCE, not structure: "returns", "exits",
# "writes", "contains the key" are all machine-checkable and stay
# automated.
STRONG_VISUAL_PATTERNS = [
    r"\brenders?\b", r"\brendering\b",
    r"\bvisible\b", r"\bvisually\b", r"\breads? as\b",
    r"\bappears?\b", r"\bon screen\b", r"\bthe page contains\b",
    r"\blabel(l?ed|s)?\b", r"\btheme\b", r"\bdark mode\b", r"\blight mode\b",
    r"\blayout\b", r"\bstyl(e|ed|ing)\b", r"\bcolou?r\b", r"\bfont\b",
    r"\bscroll(s|ing|bar)?\b", r"\bviewport\b", r"\bresponsive\b",
    r"\bin firefox\b", r"\bin chrome\b", r"\bin safari\b",
    r"\bscreenshot\b", r"\bui\b", r"\bpage reads\b",
]

# Words used constantly BOTH for what a person watched on a rendered page
# AND for what a file, command, exit code or test reports ("the log
# shows", "you see the exit code", "look at the output", "the command
# displays a count"). These block only when the criterion names nothing
# checkable (ANCHOR_PATTERNS) -- CE-2.38.
AMBIGUOUS_VISUAL_PATTERNS = [
    r"\bshows?\b", r"\bsees?\b", r"\blooks?\b", r"\bdisplays?\b",
]

# Evidence that the criterion names a concrete, checkable thing rather
# than an appearance: a file's contents, a command's output, an exit
# code, or a named test (CE-2.38, AC1's own list). Presence of any of
# these is what lets an AMBIGUOUS_VISUAL_PATTERNS hit through.
ANCHOR_PATTERNS = [
    r"\bfile\b", r"\bconfig\b", r"\.\w{1,5}\b",  # a file, or a dotted
                                                    # filename like vite.config.ts
    r"\bcommand\b", r"\boutput\b", r"\bstdout\b", r"\bstderr\b",
    r"\bexit code\b", r"\bexit status\b", r"\bexits?\b",
    r"\btest\b",
]

_TICKET_AC_ADD = re.compile(r"\bticket\b[^|;&]*\bac\b\s+add\b")


def _segments(command):
    """Split a compound shell command into candidate invocations.

    Splits on `&&`, `||`, `;` and newline -- but only OUTSIDE quotes. The
    criterion's own text is one shell argument, so a semicolon, `&&`,
    `||` or newline INSIDE that quoted --text value is data, not a
    statement separator. Splitting on the raw string tore the quoted
    argument in two: one half left with an unbalanced quote (shlex.split
    raises, so `_parse` failed open), the other half no longer containing
    `ticket ac add` at all -- so the whole call passed unjudged whatever
    its --text described (CE-2.36).
    """
    segments = []
    current = []
    quote = None  # None, "'", or '"'
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            elif quote == '"' and ch == "\\" and i + 1 < n:
                # An escaped character inside double quotes stays literal,
                # whatever it is -- including a quote or another backslash.
                current.append(command[i + 1])
                i += 1
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            current.append(ch)
            current.append(command[i + 1])
            i += 2
            continue
        if command.startswith("&&", i) or command.startswith("||", i):
            segments.append("".join(current))
            current = []
            i += 2
            continue
        if ch in (";", "\n"):
            segments.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    segments.append("".join(current))
    return segments


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


# CE-2.85 (the CSO's list review of 2026-09-25, option A1): two exact spans
# are not appearance, so they are masked before judging. Only the matched
# SPAN is masked, never every use of the word (the review's finding 4):
#   - `appears` where a stream follows it: "appears on stderr" reports what a
#     stream carries, which a test reads;
#   - `ui` inside the harness's hook order "bash, watch, pr, commit, scope,
#     ui", where it is the UAT hook's short name.
# Both words stay in STRONG_VISUAL_PATTERNS and ANCHOR_PATTERNS is unchanged,
# so "the banner appears on the page and appears on stderr" is still refused
# on its first `appears`.
_STREAM_APPEARS = re.compile(
    r"\bappears?(?=\s+(?:on|in)\s+(?:stderr|stdout|the output|the log)\b)")
_HOOK_ORDER_UI = re.compile(
    r"\b(bash,\s*watch,\s*pr,\s*commit,\s*scope,\s*)ui\b")


def _mask_exempt_spans(lowered):
    """`lowered` with the two CE-2.85 spans' visual word replaced by a word
    no pattern in this module matches."""
    lowered = _STREAM_APPEARS.sub("reported", lowered)
    return _HOOK_ORDER_UI.sub(r"\1uat-hook", lowered)


def _names_what_it_checks(lowered):
    """True if the criterion names a file, a command, an exit code or a
    test -- the four things AC1 (CE-2.38) says still count as automated
    however an everyday visual word describes them."""
    return any(re.search(p, lowered) for p in ANCHOR_PATTERNS)


def _visual_hits(text):
    """Words that make `text` read as visual, judged in two tiers.

    STRONG hits (renders, theme, layout, ...) block unconditionally --
    they describe appearance and nothing else. AMBIGUOUS hits (shows,
    see, look, display) only block when the criterion names nothing
    checkable: paired with a file, a command, an exit code or a test,
    they are the everyday sense, not a report of what someone watched
    happen on a rendered page (CE-2.38). The two CE-2.85 spans are
    masked first (_mask_exempt_spans).
    """
    lowered = _mask_exempt_spans(text.lower())
    strong = [p for p in STRONG_VISUAL_PATTERNS if re.search(p, lowered)]
    if strong:
        return strong
    ambiguous = [p for p in AMBIGUOUS_VISUAL_PATTERNS if re.search(p, lowered)]
    if ambiguous and not _names_what_it_checks(lowered):
        return ambiguous
    return []


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
