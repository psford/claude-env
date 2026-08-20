#!/usr/bin/env python3
"""Refuse `gh pr create` for a ticket that has not been accepted.

The rule is not new. `implementing-a-story` has said it since the skill was
written: "One PR per epic, not per story. Stories commit onto the epic's
branch; the PR opens once the epic's stories are accepted."

It was ignored roughly twenty times in one session, and the cost was not
tidiness. Two tickets were merged before QA ever ran; one of them had a
vacuous test, and the other's review then happened after the merge and was
written into a store that later moved, destroying the verdict and costing a
recovery ticket and a second review. It also made Patrick the review
bottleneck at the exact moment each change was least validated.

Every agent dispatched in that session was told to read the skill. The
orchestrator never read it. Skills govern the work; nothing governed the
space between tasks, which is where the drift lives -- so this is a hook
rather than a reminder.

Refused: `gh pr create` naming a ticket whose status is not `accepted`.
Allowed: an accepted ticket, a PR naming no ticket at all (release PRs from
develop to main), and anything that is not `gh pr create`.

Override, deliberately narrow and deliberately typed out in full:
  PR_BEFORE_ACCEPT_OK=1 gh pr create ...
There is a real case for it -- a draft opened for a conversation about
direction -- and an override that has to be spelled out is a decision rather
than a habit.

Exit 2 blocks the call.
"""

import json
import os
import re
import subprocess
import sys


def ticket_ids(text):
    """Ticket ids in any case, because a branch name is lower-cased by habit.

    The first version of this matched [A-Z]{2,}-\\d+ only, and my own test
    caught it: `fix/ch121-two-rails` named an unaccepted ticket and sailed
    through. A guard that reads only the spelling people use in titles, and not
    the one they use in branches, is a guard with a hole in the commonest case.
    """
    # The hyphen is optional: a title says CH-121 and a branch says ch121.
    # A false match costs nothing -- an id the store does not know returns
    # no status and is ignored -- so the pattern errs wide on purpose.
    found = re.findall(r'\b([A-Za-z]{2,})-?(\d+)\b', text or "")
    return [f"{p.upper()}-{n}" for p, n in found]


def status_of(tid, cwd):
    """The ticket's status via the CLI, or None if it cannot be read.

    Asks `ticket show` rather than reading a path: the store moved out of the
    working tree once already, and a second copy of that rule is how the two
    write-guards ended up disagreeing.
    """
    try:
        out = subprocess.run(["ticket", "show", tid], cwd=cwd, capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    m = re.search(r'^\s*status\s+(\w+)', out.stdout, re.M)
    return m.group(1) if m else None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not re.search(r'\bgh\b[^|;&]*\bpr\b[^|;&]*\bcreate\b', command):
        return 0
    if os.environ.get("PR_BEFORE_ACCEPT_OK") == "1":
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    # The title and branch name are where a story PR names its ticket. The body
    # is deliberately NOT scanned: a release PR legitimately lists every ticket
    # it carries, and scanning it would refuse exactly the PR that should open.
    head = ""
    m = re.search(r'--title\s+(["\'])(.*?)\1', command, re.S)
    if m:
        head += " " + m.group(2)
    m = re.search(r'--head[= ]+(\S+)', command)
    if m:
        head += " " + m.group(1)
    m = re.search(r'\bcheckout\b.*?-b\s+(\S+)', command)
    if m:
        head += " " + m.group(1)

    unaccepted = []
    for tid in dict.fromkeys(ticket_ids(head)):
        st = status_of(tid, cwd)
        if st is not None and st != "accepted":
            unaccepted.append((tid, st))

    if not unaccepted:
        return 0

    lines = "".join(f"  - {t} is {s}, not accepted\n" for t, s in unaccepted)
    print(
        "BLOCKED: a pull request opens once the work is accepted.\n\n"
        + lines
        + "\nfrom implementing-a-story: \"One PR per epic, not per story. Stories\n"
          "commit onto the epic's branch; the PR opens once the epic's stories\n"
          "are accepted.\"\n\n"
          "Commit to the branch, let QA judge it there, and open the PR when the\n"
          "ticket says accepted. Opening it earlier puts unreviewed work in front\n"
          "of Patrick at the moment it is least validated -- which has already\n"
          "merged a vacuous test and destroyed a QA verdict.\n\n"
          "If a draft really is the point, say so deliberately:\n"
          "  PR_BEFORE_ACCEPT_OK=1 gh pr create ...",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
