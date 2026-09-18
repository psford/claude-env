#!/usr/bin/env python3
"""Test deploy_guard hook output format.

Verifies that:
1. Deny reasons are carried under permissionDecisionReason (not "reason")
2. The deny decision itself is unchanged
3. All existing fixtures remain passing

Run: python3 .claude/hooks/tests/test_deploy_guard.py
"""

import json
import os
import subprocess
import sys
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GUARD = os.path.join(HOOKS, "deploy_guard.py")


def hook_output(command):
    """Run deploy_guard with a command and return its JSON output."""
    p = subprocess.run(
        [sys.executable, GUARD],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True, check=False)
    if p.returncode != 0:
        return f"exit_code={p.returncode}: {p.stderr!r}"
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return f"unparseable: {p.stdout!r}"


class TestDenyReason(unittest.TestCase):
    """Verify that deny reasons are exposed to agents under the right key."""

    def test_a_deny_carries_its_reason_in_permissionDecisionReason(self):
        """AC1: Deny carries message under permissionDecisionReason."""
        output = hook_output("gh workflow run ios.yml")

        # Verify this is a deny
        self.assertIsInstance(output, dict)
        self.assertIn("hookSpecificOutput", output)
        hso = output["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")

        # Verify the reason is under the right key (not "reason")
        self.assertIn("permissionDecisionReason", hso,
                      "Deny reason must be in permissionDecisionReason, not 'reason'")
        reason = hso["permissionDecisionReason"]

        # Verify it's non-empty and contains the expected text
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0, "Reason must not be empty")
        self.assertIn("GitHub workflow", reason, "Reason should explain the block")
        self.assertIn("Patrick", reason, "Reason should name who can override")

    def test_the_deny_decision_itself_is_unchanged(self):
        """AC2: The deny decision is not altered by the reason fix."""
        output = hook_output("gh workflow run ios.yml")

        # Verify it's still a deny (not allowed or asked)
        self.assertIsInstance(output, dict)
        self.assertIn("hookSpecificOutput", output)
        hso = output["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny",
                         "Deny decision must remain unchanged")

        # Verify it exits 0 (the deny is reported, not thrown)
        p = subprocess.run(
            [sys.executable, GUARD],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "gh workflow run ios.yml"}}),
            capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0, "Hook must exit 0 to report the deny")

    def test_ordinary_commands_are_untouched(self):
        """Verify that non-blocked commands remain unblocked."""
        # Non-deployment commands should return 0 with no output
        p = subprocess.run(
            [sys.executable, GUARD],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}),
            capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0)
        # Should have no output, or empty JSON
        if p.stdout.strip():
            out = json.loads(p.stdout)
            # No deny or ask should be present
            self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")


if __name__ == "__main__":
    unittest.main(verbosity=2)
