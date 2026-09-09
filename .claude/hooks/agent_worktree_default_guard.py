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
#
# CH-232.5. For the harness's verification roles the cost is not "slow" — it is
# a WRONG ANSWER. A worktree is cut from the repo's default branch, so an agent
# sent to check a commit on develop or a feat branch inspects a tree that does
# not contain it. On 2026-09-09 Clyde was asked whether `ticket new --id` worked,
# read a worktree cut from origin/main, and reported "the --id flag does not
# exist" — citing parser line numbers — for a flag that was committed, tested and
# demonstrably working. A gate that reports work-not-done for work that is done
# is worse than no gate, because it teaches you to overrule it.
#
# These five are read-only by CONTRACT, not by convention: each one's governing
# skill forbids writing code or tests, and Clyde's says so in as many words.
# Isolation buys nothing from an agent that cannot write, and costs correctness.
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
    "psford-tickets:clyde",
    "psford-tickets:qa",
    "psford-tickets:cso",
    "psford-tickets:grace",
    "psford-tickets:analyst",
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
