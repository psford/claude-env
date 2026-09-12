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

WHAT HE ACTUALLY SEES IS THE POINT, and the first version got this wrong.
He approves the COMMAND. A hook's additionalContext goes to the model's
transcript, not to his dialog -- so reading a --prompt-file and putting its
contents there displayed the prompt to the only party that already knew it.

So the prompt must be IN the command. --prompt-file is refused, stdin is
refused, and a backgrounded dispatch is refused because it shows no dialog
at all. What is left is a positional argument, which is exactly the text the
dialog will put in front of him.

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

    # A BACKGROUNDED dispatch cannot be approved, so it cannot run. Measured
    # on this guard's first real use: the "ask" decision was emitted, the
    # context appeared in the agent's own transcript, and the command RAN --
    # because a background command shows Patrick no dialog to answer. An
    # approval gate that the caller can step around by adding one parameter
    # is not a gate, and I shipped it having tested only that the hook
    # emitted the right JSON, never that it stopped anything.
    if (hook_input.get("tool_input") or {}).get("run_in_background"):
        print(
            "\n[clyde_dispatch_review_guard] BLOCKED\n\n"
            "  this dispatch is backgrounded, so no approval dialog can be\n"
            "  shown and Patrick cannot see the prompt before it runs.\n\n"
            "Run it in the foreground. The dispatch is slow and holding the\n"
            "turn is the cost of it being reviewable.\n",
            file=sys.stderr)
        return 2

    # --prompt-file CANNOT be reviewed. Patrick approves the COMMAND, and a
    # command that says `--prompt-file /tmp/x.txt` shows him a path. The
    # first version read that file and put its contents in the hook's
    # additionalContext, which goes to the MODEL's transcript, not to his
    # dialog -- so the guard displayed the prompt to the only party that
    # already knew it. He caught it the first time it mattered: "you want to
    # run clyde, but haven't given me the prompt you are going to give it."
    #
    # So the prompt must be IN the command, where the dialog will show it.
    for token in tokens:
        if token == "--prompt-file" or token.startswith("--prompt-file="):
            print(
                "\n[clyde_dispatch_review_guard] BLOCKED\n\n"
                "  --prompt-file hides the prompt behind a path. Patrick\n"
                "  approves the command, and a path is not a prompt.\n\n"
                "Pass the prompt as a positional argument so the text he is\n"
                "approving IS the text being sent. If it is too long to read\n"
                "in a dialog, it is too long for Clyde, which answers one\n"
                "question: were the acceptance criteria satisfied.\n",
                file=sys.stderr)
            return 2

    prompt, source = _prompt_of(tokens)

    if prompt is None:
        print(
            "\n[clyde_dispatch_review_guard] BLOCKED\n\n"
            f"  {source}\n\n"
            "Patrick approves every Clyde dispatch by reading the prompt it\n"
            "will send. A dispatch whose prompt cannot be displayed cannot\n"
            "be approved, and a dialog that shows nothing is a rubber\n"
            "stamp.\n\n"
            "Pass the prompt as a positional argument.\n",
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
