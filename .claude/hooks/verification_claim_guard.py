#!/usr/bin/env python3
"""Stop hook: a claim that something works carries its output, or it stays in.

CE-12.6. Patrick, 2026-09-13, after a day of assertions that rested on one
observation or none: "do I have to review every single agent dispatch you run
to ensure you're not lying to me?"

The dispatch gate does not catch this. These claims live in MESSAGES to him,
not in what is sent to agents. Four from one day, each stated as fact, each
untrue when measured:

    "the hook works"                   it never executed once
    "clyde cannot build outside its    three runs: WROTE, WROTE, blocked
     tree"
    "the ssh case is fixed"            one run, and the seam check was invalid
    "0 new refusals"                   compared HEAD against HEAD

Each was a conclusion he could not check from the text in front of him, and
each time he acted on it.

So: do not be the one who says whether something works. Report the command
and what it printed; let him draw the conclusion. Where the subject is an
agent, the RATIO goes in -- "5/5", never "blocked" -- because an agent
declining looks identical to an agent being stopped.

WHAT THIS ASKS. One question about state: does this message assert a
first-person verification while carrying no output at all. It has no opinion
about whether the claim is TRUE -- that is the intent-parsing category this
repo has spent two days failing at, and it is not what is being attempted
here.

WHAT IT DELIBERATELY LEAVES ALONE. Reporting somebody else's verdict is not
a first-person claim: "QA passed it", "Clyde failed AC1", "CSO blocked the
release" are how the board is described and must stay sayable. So the
patterns below are anchored to the first person or to a bare assertion about
the work, never to a third party's name.
"""

import json
import re
import sys

# A first-person assertion that something was checked and holds. Anchored so
# that "QA verified it" and "Clyde confirmed AC3" -- reports of another
# party's verdict -- do not match.
CLAIMS = (
    re.compile(r'\bI (?:have )?(?:verified|confirmed|tested|checked)\b', re.I),
    re.compile(r'\b(?:it|this|that|which) (?:now )?works\b', re.I),
    re.compile(r'\b(?:it|this|that) is (?:now )?(?:fixed|working|verified)\b',
               re.I),
    re.compile(r'\bworks (?:now|correctly|as expected|fine)\b', re.I),
    re.compile(r'\bverified[,:]? (?:it|this|that|the)\b', re.I),
    re.compile(r'\bconfirmed (?:working|fixed|good)\b', re.I),
)

# Evidence: a fenced block, an indented output line, or a measured ratio.
FENCE = re.compile(r'```')
RATIO = re.compile(r'\b\d+\s*/\s*\d+\b')
TABLE = re.compile(r'^\s*\|.*\|', re.M)


def last_assistant_text(transcript_path):
    try:
        with open(transcript_path, encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError:
        return ''
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        msg = entry.get('message') if isinstance(entry, dict) else None
        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
            continue
        content = msg.get('content')
        parts = []
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    parts.append(block.get('text', ''))
        if parts:
            return '\n'.join(parts)
    return ''


# Who ELSE can verify something. A claim with one of these just before it is
# a report of their verdict, not mine, and reporting the board is how the
# board gets described. The list is the safe side: a name missing from it
# costs a false refusal on a sentence I can rewrite, never a silent pass on
# a claim of my own.
OTHER_ACTORS = re.compile(
    r'\b(?:qa|clyde|cso|grace|patrick|the reviewer|the gate|the guard'
    r'|the suite|the hook|he|they)\b', re.I)


def _is_someone_elses(text, start):
    """True when a known third party is the subject just before `start`.

    WORD BOUNDARIES, not substrings. The first version tested `"he " in
    before`, and "The ssh case is fixed and it works" contains "he " inside
    "The" -- so a claim of mine was exempted by the word The.
    """
    return bool(OTHER_ACTORS.search(text[max(0, start - 40):start]))


def carries_evidence(text):
    return bool(FENCE.search(text) or RATIO.search(text) or TABLE.search(text))


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    path = data.get('transcript_path')
    if not path:
        return 0
    text = last_assistant_text(path)
    if not text:
        return 0

    found = []
    for pattern in CLAIMS:
        for m in pattern.finditer(text):
            if not _is_someone_elses(text, m.start()):
                found.append(m.group(0))
                break
    if not found or carries_evidence(text):
        return 0

    print(json.dumps({
        "decision": "block",
        "reason": (
            "BLOCKED by verification_claim_guard: this reply asserts that "
            "something was checked and holds, and carries nothing to check "
            f"it against. The phrase found: {found[0]!r}.\n\n"
            "You do not get to be the one who says whether it works. On "
            "2026-09-13 four such claims -- 'the hook works', 'clyde cannot "
            "build outside its tree', 'the ssh case is fixed', '0 new "
            "refusals' -- were each stated as fact, each rested on one "
            "observation or none, and each was acted on.\n\n"
            "Rewrite it as what you RAN and what it PRINTED. Where the "
            "subject is an agent, give the ratio (5/5), never a bare "
            "'blocked' -- an agent declining looks identical to an agent "
            "being stopped.\n\n"
            "Reporting someone else's verdict is fine and is not what this "
            "caught: 'QA passed it', 'Clyde failed AC1', 'CSO blocked the "
            "release' are untouched."
        )
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
