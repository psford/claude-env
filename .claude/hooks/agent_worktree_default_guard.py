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
# CH-232.5. For the harness's verification roles the cost is not "slow" — it is
# a WRONG ANSWER. A worktree is cut from the repo's default branch, so an agent
# sent to check a commit on develop or a feat branch inspects a tree that does
# not contain it. On 2026-09-09 Clyde was asked whether `ticket new --id` worked,
# read a worktree cut from origin/main, and reported "the --id flag does not
# exist" — citing parser line numbers — for a flag that was committed, tested and
# demonstrably working. A gate that reports work-not-done for work that is done
# is worse than no gate, because it teaches you to overrule it.
#
# The reason is NOT that these five never write. An earlier version of this
# comment claimed "each one's governing skill forbids writing code or tests",
# and QA checked it: false for four of the five. judging-test-sufficiency:152
# says "You may also write the missing test yourself." reviewing-code-quality
# has Grace write a report to docs/reviews/ and create the directory if absent.
# securing-the-push-to-main and breaking-down-an-epic say nothing about code at
# all. Only Clyde's skill carries the prohibition, and only Clyde's agent
# definition narrows the tool set (no Write, no Edit) to back it up — though
# Bash can still redirect to a file, so even there the contract is enforced by
# the role's own discipline and not by the sandbox. Say what is true.
#
# The real reason is that isolation breaks these roles in two ways at once:
#
#   1. It hides the branch they exist to inspect. A verification role handed a
#      worktree cut from the default branch is answering about the wrong tree.
#   2. It discards the artifact they were asked to produce. QA's missing test
#      and Grace's review file are written INTO the worktree and die with it,
#      so the work silently never happened.
#
# Isolation protects the main tree from an agent that might wander. These five
# are pointed AT the main tree on purpose — the tree under test is the subject,
# not a hazard. That is what makes the exemption safe, not a no-write promise
# four of them never made.
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
