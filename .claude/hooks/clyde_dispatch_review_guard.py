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
one question about state: is this command a clyde dispatch.

CE-2.45, 2026-09-15. Patrick retracted the per-dispatch approval above:
Clyde prompts are the fixed short template now, so there is no longer a
live decision for him to make on each run. A recognised dispatch is
allowed, not asked -- but the prompt it will send still goes to
additionalContext exactly as before, because "what he actually sees is
the point" did not stop being true, only the gating on it did. The
recognition logic (which command is a dispatch, what its prompt is) is
untouched; only the permissionDecision at the end changed.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    mask_data_spans, resolved_commands, strip_heredoc_bodies,
)

MAX_SHOWN = 8000        # a dialog he can actually read

# glm-agent's own flags that consume the token after them, wherever they sit
# (its parser accepts `--ticket`/`--commit` in either order, before the
# prompt). CE-2.43: a scan that only skips DASH-PREFIXED tokens leaves the
# VALUE of one of these looking like a bare word -- the first bare word after
# `glm-agent` is exactly what this file uses to find the role -- so
# `glm-agent --ticket CE-1 clyde haiku ...` read "CE-1" as the role, decided
# this was not a clyde dispatch, and asked nobody.
GLM_AGENT_VALUE_FLAGS = ("--ticket", "--commit")


def _skip_value_flags(tokens):
    """`tokens` with each (flag, value) pair in GLM_AGENT_VALUE_FLAGS removed.

    Wherever the flag sits -- glm-agent's parser does not require it in any
    particular position relative to role/tier, so a scan that only expects it
    in one spot is exactly as blind as expecting none at all.
    """
    out, skip = [], False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in GLM_AGENT_VALUE_FLAGS:
            skip = True
            continue
        out.append(token)
    return out


def _dispatches_clyde(tokens):
    """True when this argv runs `glm-agent` with the clyde role.

    The role is the FIRST positional argument -- `glm-agent clyde haiku ...`
    -- so a command that merely mentions clyde in a message, a path or a
    ticket note is not this. `tokens` is real argv, already resolved through
    any interpreter or wrapper that carried it (CE-2.43) -- the caller is
    responsible for that, not this function.
    """
    for index, token in enumerate(tokens):
        if os.path.basename(token) != "glm-agent":
            continue
        for candidate in _skip_value_flags(tokens[index + 1:]):
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

    # Everything after the role and the tier is the prompt. --ticket/--commit
    # pairs are stripped first, wherever they sit, so neither the flag nor
    # its value is ever mistaken for the role, the tier, or a word of the
    # prompt (CE-2.43) -- the same defect _dispatches_clyde had, in the
    # function that decides what Patrick is shown rather than the one that
    # decides whether he is asked at all.
    rest, skip = [], 0
    seen_role = False
    for token in _skip_value_flags(tokens):
        if skip:
            skip -= 1
            continue
        if not seen_role:
            if os.path.basename(token) == "glm-agent":
                seen_role = True
                skip = 2          # the role and the tier
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

    # A dispatch is judged on what a shell will actually RUN, not on the raw
    # string. Two things a naive split over the string gets wrong (CE-2.43):
    #
    #   TEXT is not a command. `echo glm-agent clyde haiku ...` and a heredoc
    #   BODY that merely mentions a dispatch describe one; they do not run
    #   it. mask_data_spans blanks the arguments of text-speaking commands
    #   (echo, printf, a commit message, ...) and strip_heredoc_bodies drops
    #   a heredoc's body unless it feeds an interpreter that will execute it
    #   -- the same masking ci_cost_guard and deploy_guard already judge by.
    #
    #   AN INTERPRETER is not opaque. `bash -c 'glm-agent clyde haiku ...'`
    #   runs that dispatch as surely as typing it directly, and
    #   resolved_commands descends into what `-c`'s payload actually invokes
    #   rather than stopping at "bash".
    #
    # Once real argv is in hand, `_dispatches_clyde` finds the role the same
    # way for every one of them: peeled from an interpreter or read at the
    # top level, it is one shape.
    masked = mask_data_spans(strip_heredoc_bodies(command or ""))
    found, _parsed = resolved_commands(masked)

    tokens = None
    for argv, _source, _remote in found:
        if argv and _dispatches_clyde(argv):
            tokens = argv
            break
    if tokens is None:
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

    # CE-2.45: allow, not ask. Patrick retracted the per-dispatch approval
    # this was built for (see the module docstring) -- Clyde prompts are the
    # fixed short template now, so there is no longer a per-run decision for
    # him to make. What does not change is the prompt reaching a transcript:
    # additionalContext is attached to every recognised dispatch exactly as
    # before, so the text being sent is still visible, just no longer gated
    # behind a dialog.
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
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
