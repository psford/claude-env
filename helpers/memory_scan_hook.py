#!/usr/bin/env python3
"""PreToolUse hook: scan saved memories before each consequential action.

CE-2.69. The reply-rule guard fires AFTER a reply is written; this hook puts
the matching rules in front of the actor BEFORE the action runs. Thin on
purpose: the logic lives in helpers/memory_scan.py. The orchestrator wires
this file into settings after merge; nothing here is self-installing.

Consequential means: dispatching, stopping or replacing an agent
(Agent/SendMessage/TaskStop), or a Bash command that moves a ticket, writes
git history, deploys, or opens a PR. Everything else -- reads, listings,
status reports -- passes through untouched.

Three outcomes, never a silent fourth:
  fired     -- one JSON hookSpecificOutput with additionalContext naming each
               surfaced rule's key and its How to apply text. Exit 0: the
               context is advice, not a block.
  clean     -- no output, exit 0.
  unchecked -- the scan could not run. Exit 1 with
               "memory scan NOT run: <reason>" on stderr and no deny decision
               on stdout: a broken classifier must never block an action,
               but it must be visible in the session rather than
               indistinguishable from a pass.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import memory_scan  # noqa: E402

AGENT_TOOLS = {"Agent", "SendMessage", "TaskStop"}

CONSEQUENTIAL_BASH_RES = [
    re.compile(r"\bticket\s+(move|ask|new|ac|uat|release|set|resolve)\b"),
    re.compile(r"\bgit\s+(-C\s+\S+\s+)?(merge|commit|push|checkout|reset|rebase)\b"),
    re.compile(r"\bglm-agent\b"),
    re.compile(r"\bgh\s+pr\b"),
    re.compile(r"\bwrangler\b"),
    re.compile(r"deploy"),
]


def is_consequential(tool_name, tool_input):
    if tool_name in AGENT_TOOLS:
        return True
    if tool_name != "Bash":
        return False
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return any(r.search(command) for r in CONSEQUENTIAL_BASH_RES)


def action_text_of(tool_name, tool_input):
    parts = [tool_name]
    if isinstance(tool_input, dict):
        if tool_input.get("command"):
            parts.append(tool_input["command"])
        for field in ("prompt", "description"):
            if tool_input.get(field):
                parts.append(str(tool_input[field]))
    return ": ".join(parts)


def memory_dir_of(payload):
    transcript = payload.get("transcript_path")
    if transcript:
        candidate = Path(transcript).parent / "memory"
        if candidate.is_dir():
            return candidate
    return memory_scan.default_memory_dir()


def main(payload=None, scan=None):
    scan = scan or memory_scan.scan
    if payload is None:
        try:
            payload = json.load(sys.stdin)
        except ValueError:
            print("memory scan NOT run: hook input was not JSON",
                  file=sys.stderr)
            return 1
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if not is_consequential(tool_name, tool_input):
        return 0

    result = scan(action_text_of(tool_name, tool_input),
                  memory_dir=memory_dir_of(payload))
    if result["status"] == "fired":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": memory_scan.context_lines(result["rules"]),
            }
        }))
        return 0
    if result["status"] == "unchecked":
        print(f"memory scan NOT run: {result['reason']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
