#!/usr/bin/env python3
"""Claude Code PreToolUse hook: Patrick sees a Clyde prompt before it runs.

CE-12.5. Patrick, 2026-09-13: "clyde dispatches have to be approved by me,
with the prompt you're giving him displayed in the approval."

Clyde's definition is correct as written -- one criterion, pass or fail,
writes nothing. Every deviation in a day of dispatches came from the PROMPT:
eight told it to build a scratch git repo, several told it to attack an
allowlist or hunt for what a pattern would miss, which is QA's remit, and one
told it to repeat every measurement three times when each measurement was
itself a nested agent dispatch. He corrected it mid-session and the next
prompt did it again.

So the prompt is the uncontrolled surface, and it goes in front of him.

WHAT IS SHOWN IS THE POINT. The prompt almost always arrives as
`--prompt-file <path>`, so displaying the command line displays a path and
tells him nothing. The file's CONTENTS are read and shown. A dispatch whose
prompt cannot be read -- `-`, meaning stdin -- is REFUSED rather than held,
because an approval dialog that cannot show what is being sent is a rubber
stamp, and a rubber stamp is worse than no gate at all.

This does not judge the prompt. It has no opinion about what a good Clyde
prompt looks like, and it is not trying to detect a bad one -- that is the
intent-parsing category this repo has spent two days failing at. It answers
one question about state: is this command a clyde dispatch. Then it hands
the text to the person whose call it is.
"""

import json
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import statements  # noqa: E402

MAX_SHOWN = 8000        # a dialog he can actually read


def _dispatches_clyde(tokens):
    """True when this argv runs `glm-agent` with the clyde role.

    The role is the FIRST positional argument -- `glm-agent clyde haiku ...`
    -- so a command that merely mentions clyde in a message, a path or a
    ticket note is not this.
    """
    for index, token in enumerate(tokens):
        if os.path.basename(token) != "glm-agent":
            continue
        for candidate in tokens[index + 1:]:
            if candidate.startswith("-"):
                continue
            return candidate == "clyde"
        return False
    return False


def _prompt_of(tokens):
    """(text, source) for what this dispatch will send, or (None, reason)."""
    for index, token in enumerate(tokens):
        if token == "--prompt-file" and index + 1 < len(tokens):
            path = tokens[index + 1]
            try:
                with open(path, encoding="utf-8") as handle:
                    return handle.read(), path
            except OSError as exc:
                return None, f"--prompt-file {path} could not be read ({exc})"

    # Everything after the role, the tier and any --ticket pair is the prompt.
    rest, skip = [], 0
    seen_role = False
    for index, token in enumerate(tokens):
        if skip:
            skip -= 1
            continue
        if not seen_role:
            if os.path.basename(token) == "glm-agent":
                seen_role = True
                skip = 2          # the role and the tier
            continue
        if token == "--ticket":
            skip = 1
            continue
        rest.append(token)

    if rest == ["-"]:
        return None, ("the prompt arrives on stdin, which this hook cannot "
                      "read")
    if rest:
        return " ".join(rest), "the command line"
    return None, "no prompt could be found in the command"


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = (hook_input.get("tool_input") or {}).get("command", "")

    dispatches = False
    for chunk in statements(command or ""):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            continue
        if _dispatches_clyde(tokens):
            dispatches = True
            break
    if not dispatches:
        return 0

    prompt, source = _prompt_of(tokens)

    if prompt is None:
        print(
            "\n[clyde_dispatch_review_guard] BLOCKED\n\n"
            f"  {source}\n\n"
            "Patrick approves every Clyde dispatch by reading the prompt it\n"
            "will send. A dispatch whose prompt cannot be displayed cannot\n"
            "be approved, and a dialog that shows nothing is a rubber\n"
            "stamp.\n\n"
            "Write the prompt to a file and pass --prompt-file <path>.\n",
            file=sys.stderr)
        return 2

    shown = prompt if len(prompt) <= MAX_SHOWN else (
        prompt[:MAX_SHOWN] + f"\n\n[...{len(prompt) - MAX_SHOWN} more bytes]")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "additionalContext": (
                "CLYDE DISPATCH — the prompt being sent,\n"
                f"from {source}:\n\n"
                "────────────────────────────────────────\n"
                f"{shown}\n"
                "────────────────────────────────────────\n\n"
                "Clyde answers ONE question: were the acceptance criteria\n"
                "satisfied. It writes nothing. A prompt that tells it to\n"
                "attack something, hunt for what a pattern misses, or build\n"
                "a scratch repo has exceeded that remit — every one of those\n"
                "came from the dispatcher, not from Clyde.\n"
            ),
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
