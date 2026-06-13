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

To opt out for a known read-only agent type not in the allowlist, pass
`isolation: "none"` (or any non-empty value) explicitly in the dispatch.

Input: PreToolUse JSON payload on stdin.
Output: JSON on stdout with `hookSpecificOutput.updatedInput` when forcing
worktree; nothing (silent pass) otherwise.
"""
import json
import sys


# Read-only agent types — pass through without worktree to avoid wasted setup.
# Err on the side of OMITTING; the failure mode for over-worktree is "slow,"
# the failure mode for under-worktree is "wander reaches main."
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
        f"them back. Pass an explicit `isolation` value to opt out."
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
