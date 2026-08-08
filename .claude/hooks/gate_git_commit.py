#!/usr/bin/env python3
"""Commit gate: force user approval before a git commit, unless a ticket
already answered the question.

PreToolUse hook on Bash. Returns an "ask" permission decision for a git
commit, which forces Claude Code's prompt.

This exists because Claude cannot be trusted to follow the commit protocol
through prompting alone. It stays for ad-hoc work.

WHY THE EXEMPTION
-----------------
In a ticket-driven run the prompt is not a safeguard, it is a bottleneck. A
five-story epic means five prompts for commits Patrick has no context on, has
not asked to see, and cannot meaningfully judge -- and the model is that he
gates at scope agreement, UAT, and the PR, not per commit. A gate that fires
where it cannot inform the decision trains people to click through it, which
costs more than it protects.

So the prompt is skipped only when a ticket has already asserted everything
the prompt would have asked:

  * the repo has a ticket store
  * the branch is not trunk
  * the commit message names a ticket that exists and is in_progress

That combination means the work was specified, reviewed as a story, and
claimed before a line was written. `ticket_commit_guard` in the harness
plugin enforces the same rule as a hard block; this hook only decides whether
to interrupt a human.

Everything else -- no ticket store, trunk, an unnamed or wrong-state ticket --
prompts exactly as before.
"""

import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402
    commit_tokens, target_directory, current_branch,
)

TRUNKS = {"main", "master"}



def named_ticket_is_in_progress(command, tokens, cwd):
    """True if the message names a ticket that exists and is in_progress."""
    store = os.path.join(cwd, ".claude", "tickets")
    config = os.path.join(store, "config.json")
    if not os.path.exists(config):
        return False
    try:
        with open(config) as fh:
            prefix = json.load(fh)["prefix"]
    except Exception:
        return False

    # The whole command string carries -m values and heredoc bodies; a -F file
    # has to be read.
    text = command
    for flag in ("-F", "--file"):
        if flag in tokens:
            idx = tokens.index(flag)
            if idx + 1 < len(tokens) and tokens[idx + 1] != "-":
                path = tokens[idx + 1]
                if not os.path.isabs(path):
                    path = os.path.join(cwd, path)
                try:
                    with open(path) as fh:
                        text += "\n" + fh.read()
                except OSError:
                    pass

    for tid in dict.fromkeys(re.findall(rf'\b{re.escape(prefix)}-\d+\b', text)):
        try:
            with open(os.path.join(store, f"{tid}.json")) as fh:
                if json.load(fh).get("status") == "in_progress":
                    return True
        except Exception:
            continue
    return False


def allow(context=None):
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "permissionDecision": "allow"}}
    if context:
        out["hookSpecificOutput"]["additionalContext"] = context
    return out


def main():
    try:
        data = json.loads(sys.stdin.read())
        command = (data.get("tool_input") or {}).get("command", "")

        tokens = commit_tokens(command)
        if tokens is None:
            print(json.dumps(allow()))
            return

        cwd = target_directory(command, default=(data.get("cwd") or os.getcwd()))
        branch = current_branch(cwd)

        if branch and branch not in TRUNKS and named_ticket_is_in_progress(command, tokens, cwd):
            print(json.dumps(allow(
                "[commit-gate] ticket-driven commit on a feature branch: "
                "the ticket already asserts this work was specified and claimed. "
                "Not interrupting.")))
            return

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "additionalContext": (
                    "[commit-gate] git commit detected. "
                    "Review the commit message and approve or deny."
                ),
            }
        }))

    except Exception:
        # Never break the system -- but a commit we could not classify still
        # deserves a human, so ask rather than allow.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "additionalContext": "[commit-gate] could not classify this commit; asking.",
            }
        }))


if __name__ == "__main__":
    main()
