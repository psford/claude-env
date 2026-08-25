#!/usr/bin/env python3
"""PreToolUse/Bash guard: refuse `cd` into a directory outside the workspace.

THE FAILURE THIS EXISTS FOR, observed repeatedly on 2026-08-24.

The harness resets the shell to the PRIMARY working directory whenever a command
leaves cwd outside the allowed set. Reproduced in one command:

    $ cd /tmp && pwd
    /tmp
    Shell cwd was reset to /home/patrick/projects/claude-env

So a command that cds into the scratchpad under /tmp -- which every
mutation-test backup-and-restore did -- silently relocates the shell to
claude-env. The NEXT command then runs against the wrong repository, and the
symptoms are baffling rather than obvious:

  - `ticket show CH-188` -> "no such ticket", because it resolved claude-env's
    store instead of claude-harness's
  - a `git commit` landing in claude-env when the work was for claude-harness
  - `ls docs/test-plans/CH-186.md` -> "No such file", from the wrong root

Each of those cost real time on 2026-08-24, and none of them mentions cwd.

Patrick, 2026-08-24: "we work on a lot of projects and relative paths have
bitten us since early days."

WHY A GUARD RATHER THAN A RULE. Every enforced rule in this repo held that day;
every rule that was only written down got broken, including ones loaded into
context at session start. A relative path is convenient in the moment and the
cost lands three commands later on somebody else's repo.

THE FIX IS ALWAYS THE SAME, and it is not a workaround: use absolute paths.
Nothing needs `cd` into a scratchpad -- `cp /abs/src /abs/dst` works, and
`git -C <repo>` runs git anywhere without moving.
"""
import json
import re
import sys

# `cd` into a temp/scratch location: the shape that triggers the reset. Matched
# at a command boundary so `cd` inside a word (e.g. `abcd`) is not caught.
CD_OUTSIDE = re.compile(
    r'(?:^|[;&|]\s*|\s&&\s*|\s\|\|\s*)cd\s+(/tmp\S*|/var/tmp\S*)',
    re.IGNORECASE,
)

ESCAPE = "CWD_DRIFT_OK"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our business to fail a malformed event

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if ESCAPE in command:
        return 0

    match = CD_OUTSIDE.search(command)
    if not match:
        return 0

    target = match.group(1)
    sys.stderr.write(
        f"BLOCKED: `cd {target}` puts the shell outside the workspace.\n"
        "  The harness resets cwd to claude-env when that happens, so the NEXT\n"
        "  command runs against the wrong repo -- and the error it produces will\n"
        "  not mention directories. On 2026-08-24 this produced 'no such ticket'\n"
        "  for a ticket that existed, and a commit landing in the wrong repository.\n"
        "\n"
        "  Use absolute paths instead of moving:\n"
        "    cp /abs/source /abs/dest              rather than cd + cp\n"
        "    git -C /home/patrick/projects/<repo>  rather than cd + git\n"
        "    python3 /abs/script.py                rather than cd + python3\n"
        "\n"
        f"  If a command genuinely must run from there, say so: add {ESCAPE} to it.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
