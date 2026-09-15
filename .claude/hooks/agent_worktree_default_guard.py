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

CE-2.44 (refiling CE-2.30). Forcing isolation is the wrong answer for a role
that JUDGES a commit -- psford-tickets:clyde and psford-tickets:qa exist to
answer "did THIS commit satisfy the criteria," and Claude Code, not this
hook, picks the commit an Agent-tool worktree starts from. This hook can
force isolation on or off; it cannot pin the base commit. So a reviewing
role forced into a worktree can silently review whatever commit worktree
happened to start from, and a pass against main reads exactly like a pass
against the work under review. Only glm-agent pins the commit under review
(it takes `--commit` directly), so a role that judges a commit is refused
outright, before any agent starts, and pointed at glm-agent instead of
being isolated.

The safe side is enumerated, not the unsafe side: within the psford-tickets
namespace, only roles Patrick has ruled do not judge a commit (below, in
KNOWN_NON_REVIEWER_ROLES) are dispatched at all. Everything else in that
namespace -- clyde and qa by name, and any verdict role added later -- is
refused the same way, visibly, instead of silently passing with forced
isolation. Roles outside the psford-tickets namespace are unaffected; this
hook still only forces or respects isolation for them.

Input: PreToolUse JSON payload on stdin.
Output: JSON on stdout with `hookSpecificOutput.updatedInput` when forcing
worktree, or `hookSpecificOutput.permissionDecision: "deny"` when refusing
a reviewing role; nothing (silent pass) otherwise.
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


PSFORD_TICKETS_NAMESPACE = "psford-tickets:"

# psford-tickets roles Patrick has ruled do NOT judge a commit (CE-2.44).
# Everything else in the psford-tickets namespace -- clyde and qa by name,
# and any verdict role filed later -- is refused by dispatch_review_denial
# below rather than isolated. This is his list to extend, the same way
# READ_ONLY_AGENTS above is his list: adding a role here is a ruling about
# what that role is allowed to do, not a default to fall back on.
KNOWN_NON_REVIEWER_ROLES = frozenset({
    "psford-tickets:dev",
    "psford-tickets:analyst",
    "psford-tickets:planner",
    "psford-tickets:grace",
    "psford-tickets:cso",
})


def dispatch_review_denial(subagent_type):
    """The deny reason for `subagent_type`, or None if it may proceed.

    Only the psford-tickets namespace is judged here -- every other
    dispatch keeps exactly today's behaviour (forced isolation, or a
    silent pass for READ_ONLY_AGENTS). Within that namespace, the safe
    side is enumerated: a role not on KNOWN_NON_REVIEWER_ROLES is refused,
    whether it is a role known to judge a commit (clyde, qa) or one this
    hook has never seen before.
    """
    if not subagent_type.startswith(PSFORD_TICKETS_NAMESPACE):
        return None
    if subagent_type in KNOWN_NON_REVIEWER_ROLES:
        return None
    return (
        f"BLOCKED: {subagent_type} is not on the list of psford-tickets "
        "roles known not to judge a commit "
        f"({', '.join(sorted(KNOWN_NON_REVIEWER_ROLES))}), so this guard "
        "treats it as one that does.\n\n"
        "Claude Code picks the commit an Agent-tool worktree starts from, "
        "not this hook -- forcing isolation on a reviewing role would let "
        "it silently judge whatever commit worktree happened to start "
        "from, and a pass against main would read exactly like a pass "
        "against the work under review.\n\n"
        "Dispatch through glm-agent instead, which pins the commit under "
        "review with --commit. If this role genuinely does not judge a "
        "commit, that is Patrick's ruling to make by adding it to "
        "KNOWN_NON_REVIEWER_ROLES in this hook -- not a case to route "
        "around here."
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return

    # CE-2.14. A non-string subagent_type crashed this open. `in` against a
    # frozenset hashes its left operand, so a list or a dict raised TypeError,
    # the hook exited 1 with a traceback, and NO isolation was applied -- a
    # guard failing open on malformed input, against its own stated contract
    # that it always exits 0.
    #
    # Coerced to "" rather than rejected, because "" is not in the allowlist and
    # therefore isolates: an agent type this hook cannot recognise is exactly
    # the one that should get a worktree, not an exemption.
    subagent_type = tool_input.get("subagent_type") or ""
    if not isinstance(subagent_type, str):
        subagent_type = ""

    # CE-2.44. Judged before the "respect explicit isolation" bypass below,
    # and before READ_ONLY_AGENTS: neither an explicit isolation value nor a
    # read-only reputation fixes the actual problem, which is that THIS HOOK
    # cannot choose the commit an Agent-tool dispatch reviews -- only
    # glm-agent can. So a reviewing role is refused outright, whatever else
    # the dispatch says.
    denial = dispatch_review_denial(subagent_type)
    if denial is not None:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": denial,
            }
        }))
        print(denial, file=sys.stderr)
        return

    # Respect explicit isolation values from the dispatcher.
    existing = tool_input.get("isolation")
    if existing:
        return

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
