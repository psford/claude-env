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

Not refused: an `--ongoing` epic. Such an epic "names a CATEGORY, not an
outcome -- it is exempt from auto-close and can never be accepted", so
demanding it reach `accepted` is a deadlock rather than a gate: no story filed
under Maintenance could ever ship. Its stories are judged as usual.

There is NO override. The escape-hatch env-var this guard once honored was
deleted on 2026-08-31 at Patrick's direction after four uses in one night,
each locally justified -- the pattern every self-serve hatch decays into.
(The variable is deliberately not named here: the acceptance criterion is
that this file contains zero mentions of it, so nothing in the file can be
mistaken for a live mechanism.) Bypassing it
also cost more than review order: a raw `gh pr create` skips `ticket
release`, so no release ticket exists and merges stop announcing to the
board. If opening early is genuinely needed, that is Patrick's decision made
with Patrick's hands: he opens the PR from his own terminal, where this hook
does not run.

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

    The second version stopped at the dot, so `CE-2.8` read as `CE-2`. It
    refused the real release PR for CE-5 + CE-2.8 on 2026-08-30: the accepted
    story was never looked at, and the guard judged the release against its
    parent -- an ongoing epic that can never be accepted. A story id has to
    survive being read.
    """
    # The hyphen is optional: a title says CH-121 and a branch says ch121.
    # The dotted tail is part of the id, not a sentence ending.
    # A false match costs nothing -- an id the store does not know returns
    # no status and is ignored -- so the pattern errs wide on purpose.
    found = re.findall(r'\b([A-Za-z]{2,})-?(\d+(?:\.\d+)*)', text or "")
    return [f"{p.upper()}-{n}" for p, n in found]


def ticket_state(tid, cwd):
    """(status, ongoing) via the CLI, or (None, False) if it cannot be read.

    Asks `ticket show` rather than reading a path: the store moved out of the
    working tree once already, and a second copy of that rule is how the two
    write-guards ended up disagreeing. `--json` rather than the human output,
    because `ongoing` is a field there and a sentence in the other -- and a
    guard that infers a flag from prose is one rewording away from wrong.
    """
    try:
        out = subprocess.run(["ticket", "show", tid, "--json"], cwd=cwd,
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None, False
    if out.returncode != 0:
        return None, False
    try:
        data = json.loads(out.stdout)
    except ValueError:
        return None, False
    status = data.get("status")
    return (status if isinstance(status, str) else None), bool(data.get("ongoing"))


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
        st, ongoing = ticket_state(tid, cwd)
        if st is None or st == "accepted":
            continue
        # An ongoing epic has no accepted state to reach. Blocking on it would
        # mean nothing filed under a category epic can ever open a PR.
        if ongoing:
            continue
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
          "There is no override. If opening early is genuinely needed, that is\n"
          "Patrick's call and Patrick's terminal.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
