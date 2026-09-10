#!/usr/bin/env python3
"""
agent_worktree_default_guard.py — PreToolUse hook for the Agent tool.

Forces isolation="worktree" on every Agent dispatch unless:
  - the dispatch already specifies an isolation value (respect it), OR
  - the subagent_type is in the read-only allowlist below.

Why: structural enforcement so a wandered subagent can't contaminate the
main tree. Out-of-scope changes are visible as a diff between the worktree
and main and can be discarded without touching the main checkout. The
200-500ms worktree-setup cost is a rounding error vs. unwinding one
wandered agent (see [[project-agent-reliability-mitigations]] memory).

To opt out for a known read-only agent type, add it to READ_ONLY_AGENTS below.
That is the ONLY opt-out that works.

This docstring used to say "pass `isolation: \"none\"` (or any non-empty
value)". It does not work and cannot be made to: the Agent tool's `isolation`
enum accepts only "worktree" and "remote", so "none" is rejected before this
hook is ever reached, and the two legal values both mean "isolate me". An agent
following that instruction gets a validation error, not an exemption (CH-232.5,
2026-09-09 — found while trying to use it).

Naming the agent type is therefore the real mechanism, and it is the better one
anyway: an exemption granted per-dispatch is a decision made by whoever is in a
hurry, while an exemption granted per-type is a decision about what that role is
allowed to do, reviewed once.

Input: PreToolUse JSON payload on stdin.
Output: JSON on stdout with `hookSpecificOutput.updatedInput` when forcing
worktree; nothing (silent pass) otherwise.
"""
import json
import sys


# Read-only agent types — pass through without worktree to avoid wasted setup.
# Err on the side of OMITTING; the failure mode for over-worktree is "slow,"
# the failure mode for under-worktree is "wander reaches main."
#
# This list is Patrick's. Adding an agent type to it relaxes a control, which is
# his decision and not an agent's. On 2026-09-09 I added five entries without
# being asked and wrote an argument for them here; he reverted both. Do not
# re-add them, and do not leave a case for them sitting in this file.
#
READ_ONLY_AGENTS = frozenset({
    "Explore",
    "Plan",
    "claude-code-guide",
    "ed3d-research-agents:internet-researcher",
    "ed3d-research-agents:codebase-investigator",
    "ed3d-research-agents:combined-researcher",
    "ed3d-research-agents:remote-code-researcher",
    "patricks-workflow:artifact-analyzer",
    "patricks-workflow:mitigation-researcher",
})


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return

    # Respect explicit isolation values from the dispatcher.
    existing = tool_input.get("isolation")
    if existing:
        return

    subagent_type = tool_input.get("subagent_type") or ""
    if subagent_type in READ_ONLY_AGENTS:
        return

    updated = dict(tool_input)
    updated["isolation"] = "worktree"

    reason = (
        f"Defaulting to isolation=\"worktree\" for "
        f"{subagent_type or 'unspecified'} agent. Structural protection so "
        f"out-of-scope changes can't reach main until the orchestrator merges "
        f"them back. To exempt a role that must read or write the real tree, "
        f"add its agent type to READ_ONLY_AGENTS in this hook — that is the "
        f"only opt-out that works, since the isolation enum has no value "
        f"meaning \"do not isolate\"."
    )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
            "updatedInput": updated,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
