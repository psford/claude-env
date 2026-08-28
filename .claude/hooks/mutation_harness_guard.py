#!/usr/bin/env python3
"""PreToolUse: refuse a throwaway mutation-testing harness.

Patrick killed a session on 2026-08-27 over "faffing about endlessly on
mutation tests", and the very next session produced four more of them -- a
fresh copy-the-repo-and-run-the-suite script per story, plus three full gate
sweeps. Being told did not stop it, and neither did a memory entry. This is
the hard block.

> "it is not your job to endlessly try to break my software. it is the job of
>  QA to see if the AC passes."

What it matches is the SIGNATURE those four scripts shared, not the word
"mutation": copy a repository, then run a test suite inside the copy. That is
what a mutation harness is, and it is a shape almost nothing else has. Matching
on names would be trivially sidestepped by choosing a different filename, which
is the failure mode of a guard written against vocabulary instead of behaviour.

Standing approval to USE mutation testing is not an instruction to build a new
driver per ticket. A repo that wants one keeps it as a committed, reviewed tool
-- claude-harness has `mutation_smoke.py` -- and that is what ALLOWLIST names.
Growing that list is Patrick's call, deliberately: an env-var escape would be
one the agent sets for itself, which is not a gate.

Blocks with exit 2. Reading, running and editing an allowlisted driver are all
untouched.
"""

import json
import os
import re
import sys

# Committed, reviewed drivers. A path ENDING with one of these is exempt, so
# the same tool is exempt in a worktree or a temp copy of the repo.
ALLOWLIST = (
    "plugins/psford-tickets/tests/mutation_smoke.py",
    "plugins/psford-tickets/tests/test_mutation_smoke.py",
)

# Half one: the script takes a copy of a repository.
COPIES_A_REPO = (
    re.compile(r'\bcopytree\s*\('),
    re.compile(r'\bgit\b[^\n]{0,40}\bworktree\s+add\b'),
    re.compile(r'\bgit\b[^\n]{0,40}\bclone\b'),
)

# Half two: and runs a test suite inside it.
RUNS_A_SUITE = (
    re.compile(r'run-checks\.sh'),
    re.compile(r'tests?/test_[A-Za-z0-9_]+\.py'),
    re.compile(r'\b(?:pytest|unittest)\b'),
    re.compile(r'\bnpm\s+(?:test|run\s+test)\b'),
)

WATCHED_SUFFIXES = (".py", ".sh", ".bash", ".ps1")


def is_allowlisted(path):
    p = path.replace(os.sep, "/")
    return any(p.endswith(a) for a in ALLOWLIST)


def offending(content):
    """(copy_hit, suite_hit) when the content is a harness, else None."""
    copies = next((r.pattern for r in COPIES_A_REPO if r.search(content)), None)
    if not copies:
        return None
    runs = next((r.pattern for r in RUNS_A_SUITE if r.search(content)), None)
    if not runs:
        return None
    return copies, runs


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Unreadable payload is not a violation. A PreToolUse hook that exits
        # non-zero on malformed input blocks every write in the session.
        return 0

    if hook_input.get("tool_name", "") not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = hook_input.get("tool_input", {}) or {}
    path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not path or not path.lower().endswith(WATCHED_SUFFIXES):
        return 0
    if is_allowlisted(path):
        return 0

    # Every shape the write tools carry content in. Edit sends the replacement
    # rather than the whole file, and a harness assembled by successive edits
    # is the same harness.
    content = " ".join(str(tool_input.get(k, "")) for k in
                       ("content", "new_string", "new_str"))
    for edit in tool_input.get("edits", []) or []:
        if isinstance(edit, dict):
            content += " " + str(edit.get("new_string", ""))

    hit = offending(content)
    if not hit:
        return 0

    copies, runs = hit
    print(
        "BLOCKED: this is a throwaway mutation-testing harness.\n"
        f"  {path}\n"
        f"  It copies a repo (/{copies}/) and runs a suite inside it (/{runs}/).\n"
        "\n"
        "Patrick, 2026-08-28: \"it is not your job to endlessly try to break my\n"
        "software. it is the job of QA to see if the AC passes.\"\n"
        "\n"
        "A green suite plus a passing acceptance criterion is a COMPLETE answer.\n"
        "Mutating it four ways is not extra rigour, it is burning time he has\n"
        "twice told you to stop burning.\n"
        "\n"
        "The way forward:\n"
        "  1. Run the AC's tests. If they pass, say so and move on.\n"
        "  2. If you have a SPECIFIC doubt -- an assertion may be vacuous, a\n"
        "     guard may be unreachable -- say what the doubt is, out loud, and\n"
        "     use the repo's committed driver if it has one.\n"
        "  3. A genuinely new driver is a reviewed, committed tool, not a\n"
        "     scratch file. Ask Patrick to add its path to ALLOWLIST in\n"
        "     .claude/hooks/mutation_harness_guard.py.\n"
        "\n"
        "There is no environment-variable escape, deliberately: one the agent\n"
        "can set for itself is not a gate.",
        file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
