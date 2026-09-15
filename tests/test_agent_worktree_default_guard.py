#!/usr/bin/env python3
"""agent_worktree_default_guard refuses a reviewing role dispatched through
the Agent tool (CE-2.44, refiling CE-2.30).

Claude Code picks the commit an Agent-tool worktree starts from -- this
guard cannot choose it, only force isolation on or off (see the guard's own
docstring). Forcing isolation on psford-tickets:clyde or psford-tickets:qa,
as fixtures 14 and 15 used to require, means the reviewer silently judges
whatever commit worktree happened to start from: a pass against main reads
exactly like a pass against the work under review. Only glm-agent pins the
commit under review, so a role that judges a commit is refused outright,
before any agent starts, and pointed at glm-agent instead.

Why this is a unit test rather than a fixture: the fixture driver
(.claude/hooks/tests/agent_worktree_default_guard/_invoke.sh) can only tell
an injected `isolation: worktree` from silence -- it has no BLOCK case for
"deny before any agent starts" versus "forced isolation." That is also why
fixtures 14 and 15, which used to pin clyde and qa as still-isolated, had to
change with this story rather than gain new fixture rows.
"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "agent_worktree_default_guard.py")


def _decision(subagent_type):
    """The hook's full JSON output for an Agent dispatch of `subagent_type`,
    or None if the hook stayed silent (exit 0, no stdout) -- which is the
    "allow, unchanged" answer this guard gives everything it does not
    force isolation on or refuse."""
    payload = json.dumps({
        "tool_name": "Agent",
        "session_id": "test-session",
        "tool_input": {
            "subagent_type": subagent_type,
            "description": "CE-2.44 test dispatch",
            "prompt": "test prompt, never a real dispatch",
        },
    })
    result = subprocess.run([sys.executable, HOOK], input=payload,
                            capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


class TestAReviewerDispatch(unittest.TestCase):
    def test_a_commit_judging_role_is_refused_and_pointed_at_glm_agent(self):
        """psford-tickets:clyde and psford-tickets:qa both judge a commit.
        Neither is on READ_ONLY_AGENTS, so at HEAD they are dispatched with
        isolation forced to worktree -- fixtures 14 and 15 pinned exactly
        that. This story refuses both before any agent starts, and the
        refusal names glm-agent as the dispatch path that pins the commit
        under review (AC1)."""
        for subagent_type in ("psford-tickets:clyde", "psford-tickets:qa"):
            with self.subTest(subagent_type=subagent_type):
                out = _decision(subagent_type)
                self.assertIsNotNone(
                    out,
                    f"{subagent_type} dispatch was allowed silently, with "
                    "no refusal at all")
                hook_out = out.get("hookSpecificOutput", {})
                self.assertEqual(
                    "deny", hook_out.get("permissionDecision"),
                    f"{subagent_type} dispatch was not denied: {out}")
                reason = hook_out.get("permissionDecisionReason", "")
                self.assertIn(
                    "glm-agent", reason,
                    f"{subagent_type} refusal did not name glm-agent as "
                    f"the dispatch path that pins the commit: {reason!r}")

    def test_an_unlisted_psford_tickets_role_is_refused(self):
        """The safe side is enumerated (dev, analyst, planner, grace, cso),
        not the unsafe side, so a psford-tickets role that is neither on
        that list nor on READ_ONLY_AGENTS is refused the same way a
        commit-judging role is -- a verdict role added later is refused
        visibly instead of quietly passing with forced isolation (AC2)."""
        subagent_type = "psford-tickets:some-future-role"
        out = _decision(subagent_type)
        self.assertIsNotNone(
            out,
            f"{subagent_type} dispatch was allowed silently, with no "
            "refusal at all")
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(
            "deny", hook_out.get("permissionDecision"),
            f"{subagent_type} dispatch was not denied: {out}")
        reason = hook_out.get("permissionDecisionReason", "")
        self.assertIn(
            "glm-agent", reason,
            f"{subagent_type} refusal did not name glm-agent as the "
            f"dispatch path that pins the commit: {reason!r}")


if __name__ == "__main__":
    unittest.main()
