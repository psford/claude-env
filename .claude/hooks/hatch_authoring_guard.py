#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the guards' author cannot write himself a door.

CE-12.2, AC3 and AC4. Patrick, 2026-08-31: "we will never build another api
endpoint that you are allowed to use to bypass a hook." The rule held for
hatches an agent USED. It did nothing about hatches an agent WROTE.

CWD_DRIFT_OK is the case this exists for. No human designed it. A Claude
session authoring cwd_drift_guard gave it an environment-variable escape,
printed the exact string in the refusal, and a later Claude session read
that refusal and used it. Both halves were the same party: the one the
guard exists to stop.

So two mechanical checks, run before a commit that touches .claude/hooks/.

AC4 -- A NEW EXCEPTION CANNOT BE ADDED QUIETLY. Every exception that exists
today is written down in hatch_inventory.json. A token that is not in that
file is refused at authoring time. Being listed is not approval: every
entry reads "judged": "pending" until Patrick rules, and the file IS the
CE-12 work list.

AC3 -- A REFUSAL NEVER HANDS OUT ITS OWN KEY. A guard may not print its own
exception token in the text an agent reads. Ten guards did, which is how
one of them taught a later session the string that turned it off. Patrick
reads CLAUDE.md and the source; the agent reads the refusal, and the
refusal is where the key must not be.

WHAT IS ALLOWED, DELIBERATELY. Reading os.environ is fine. A `VAR=1 <cmd>`
prefix sets the environment of the command bash runs, NOT of the hook that
judged it, and shell state does not survive between tool calls -- so only
the shell that LAUNCHES the session can set one. That is the shape the
shared rules permit, and it is why this file draws its line at the COMMAND
TEXT rather than at the word "exception": the finite question is not what
an exception looks like, it is who can reach it.

This guard has no exception of its own. That is not an oversight.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import enter_target_repo  # noqa: E402
from hatch_shape_scan import waivers  # noqa: E402

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY = os.path.join(HOOK_DIR, "hatch_inventory.json")
INVENTORY_REL = ".claude/hooks/hatch_inventory.json"

IS_COMMIT = re.compile(r'\bgit\b[^|;&]*\bcommit\b')

# A hyphenated magic token, the shape every command-text hatch uses:
#   # PARK-OK: reason        <!-- BRANCH-OK: reason -->
#
# The colon may be separated from the token by regex whitespace-escapes,
# because that is how these are actually DEFINED rather than documented:
#   re.compile(r'#\s*PARK-OK\s*:')
# Measured: without this, a new hatch written only as a regex -- the normal
# way to write one -- walked past the inventory check entirely.
TOKEN = re.compile(r'\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)(?:\\+s\*?|\s)*:')

# Lines that DEFINE the pattern rather than advertise it. A regex naming the
# token is the mechanism; a string printed to stderr is the advertisement.
DEFINES = re.compile(r're\.compile|re\.(search|match|findall)|^\s*#')


def _load_inventory():
    """(every known token, the ones forbidden from appearing in output).

    `advertise: false` is set only when Patrick has JUDGED a token. Until
    then a guard keeps printing what it always printed -- silently changing
    31 refusal messages on nobody's authority would be its own kind of
    freelancing. The check is not vacuous, because PARK-OK is judged.
    """
    try:
        with open(INVENTORY) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None, None
    known, silent = set(), set()
    for kind in ("launch_shell_env", "command_text_token", "not_a_hatch"):
        for row in data.get(kind, []):
            token = row.get("token", "")
            known.add(token)
            if row.get("advertise") is False:
                silent.add(token)
    return known, silent


def _staged():
    r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                       capture_output=True, text=True)
    return [ln.strip() for ln in r.stdout.split("\n") if ln.strip()]


# CE-12.4. Every file under the hooks directory, not only .py. A hatch in a
# shell hook was invisible to the first version for no reason other than its
# extension.
#
# CE-12.10. The inventory lives at exactly this prefix and is not a hook
# file: it is the record the hook files are judged against. Counting it as
# one made a commit staging only the inventory trip the "staged alongside a
# hook file" check against itself -- refused with the message that tells
# the author to make exactly that commit. `_inventory_is_staged` below still
# reads the raw staged list, so a hook file staged WITH the inventory is
# unaffected by this exclusion.
def _staged_hook_files(staged):
    return [p for p in staged if p.startswith(".claude/hooks/")
            and not p.startswith(".claude/hooks/tests/")
            and p != INVENTORY_REL]


def _inventory_is_staged(staged):
    """True when this commit also edits the record it is judged against.

    CE-12.4. The inventory is the only thing between the author and a fresh
    hatch, and nothing watched edits to it -- so adding an entry and using
    that token in the SAME commit passed, because the scan reads .py files
    and never saw the .json diff. Content cannot tell Patrick's edit from
    mine at this layer, so the answer is not to judge the edit but to refuse
    the COMBINATION. A commit may change the record, or it may change a
    guard, and not both at once; split apart, the addition is visible on its
    own.
    """
    return INVENTORY_REL in staged


def _advertises(text, token):
    """Line numbers where `token` appears in text an agent will READ.

    A regex or a comment is the mechanism and is left alone. A quoted string
    is output, and output is where the key must not be.
    """
    hits = []
    for number, line in enumerate(text.split("\n"), 1):
        if token not in line:
            continue
        if DEFINES.search(line):
            continue
        if '"' in line or "'" in line:
            hits.append(number)
    return hits


def _refuse(lines):
    print("\n".join(lines), file=sys.stderr)
    return 2


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = (hook_input.get("tool_input") or {}).get("command", "")
    if not IS_COMMIT.search(command):
        return 0

    enter_target_repo(hook_input)
    known, silent = _load_inventory()
    if known is None:
        return _refuse([
            "[hatch_authoring_guard] BLOCKED",
            "",
            "hatch_inventory.json is missing or unreadable, so no commit to",
            "the hooks can be judged. Restore it rather than removing this",
            "check -- deleting the record is how the record stops working.",
        ])

    staged = _staged()
    hook_files = _staged_hook_files(staged)

    if hook_files and _inventory_is_staged(staged):
        return _refuse([
            "[hatch_authoring_guard] BLOCKED",
            "",
            "  this commit edits hatch_inventory.json AND a file under",
            "  .claude/hooks/, so it could add an exception and use it in the",
            "  same breath. The record cannot police a change it is part of.",
            "",
            "Commit them separately. The inventory change lands on its own,",
            "where an addition is visible as one, and the guard change is",
            "then judged against a record that already existed.",
        ])

    problems = []
    # This file is NOT skipped. The first version excused itself so its own
    # documentation would not trip the scan, which handed the author the one
    # file where a door could be written unwatched -- in the guard whose
    # whole purpose is that the author cannot write himself a door.
    for path in hook_files:
        try:
            with open(path) as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        # CE-12.4. The structural scan, which finds a waiver by its SHAPE
        # rather than by the spelling of its token: `if <literal> in
        # <command>: return 0` abandons the check, while the negation of it
        # merely decides the guard does not apply. Measured across all 51
        # hooks: nine of the second, one of the first. That one,
        # engines_node_guard's `--ignore-engines`, was a live hatch that the
        # spelling scan had never seen.
        if path.endswith(".py"):
            for line, token in waivers(text):
                if token not in known:
                    problems.append(
                        f"  {path}:{line}: waives the check on {token!r} "
                        f"found in the command text, and that is not in "
                        f"hatch_inventory.json")

        for match in set(m.group(1) for m in TOKEN.finditer(text)):
            if match not in known:
                problems.append(
                    f"  {path}: introduces the exception token {match!r}, "
                    f"which is not in hatch_inventory.json")
            elif match in silent:
                where = _advertises(text, match)
                if where:
                    problems.append(
                        f"  {path}: prints its own exception token {match!r} "
                        f"in agent-readable output, at line(s) "
                        f"{', '.join(str(n) for n in where[:5])}")

    if not problems:
        return 0

    return _refuse([
        "[hatch_authoring_guard] BLOCKED",
        "",
        *problems,
        "",
        "CE-12.2. The party writing the guards is the party the guards exist",
        "to stop. CWD_DRIFT_OK was not inherited: a Claude session wrote it,",
        "printed it in its own refusal, and a later session read that refusal",
        "and used it.",
        "",
        "A NEW token: there is no sanctioned way to add one from here. If a",
        "block is wrong, fix the guard so it stops being wrong, or report it",
        "and stop. Both are in the shared rules under 'a wrong block is a",
        "defect, not a detour'.",
        "",
        "An ADVERTISED token: take it out of the message. The mechanism can",
        "stay; handing the reader the key cannot. Patrick has CLAUDE.md and",
        "the source. The agent has only what the refusal says.",
        "",
        "This guard has no bypass, including for itself.",
    ])


if __name__ == "__main__":
    sys.exit(main())
