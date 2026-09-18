#!/usr/bin/env python3
"""Test that ci_cost_guard wirings in infrastructure/claude-settings/user-settings.json
are gated to Darwin, since iOS builds only work on macOS.

CE-25.1. The shared template is installed on non-Darwin hosts and a reinstall
would bring ci_cost_guard back if the gate is not in the template itself.

Run: python3 .claude/hooks/tests/test_user_settings_template.py
"""
import json
import os
import sys
import unittest

# Get the path to infrastructure/claude-settings/user-settings.json
# relative to the .claude/hooks/tests directory
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "infrastructure", "claude-settings",
                              "user-settings.json")


class TestDarwinGating(unittest.TestCase):
    """Test that ci_cost_guard commands are gated to Darwin."""

    def setUp(self):
        """Load the template JSON file."""
        with open(TEMPLATE_PATH, 'r') as f:
            self.settings = json.load(f)

    def test_every_ci_cost_guard_wiring_is_gated_to_darwin(self):
        """Every ci_cost_guard command in PreToolUse hooks must start with
        the Darwin gate: [ "$(uname)" = Darwin ] || exit 0;

        This ensures the hook never runs on non-Darwin hosts, since iOS builds
        only work on macOS.
        """
        darwin_gate = '[ "$(uname)" = Darwin ] || exit 0;'

        # Find all PreToolUse hooks
        pre_tool_use = self.settings.get("hooks", {}).get("PreToolUse", [])
        self.assertIsNotNone(pre_tool_use, "PreToolUse hooks not found")

        found_ci_cost_guard = False
        for hook_group in pre_tool_use:
            hooks = hook_group.get("hooks", [])
            for hook in hooks:
                command = hook.get("command", "")
                # Check if this is a ci_cost_guard command
                if "ci_cost_guard.py" in command:
                    found_ci_cost_guard = True
                    self.assertTrue(
                        command.startswith(darwin_gate),
                        f"ci_cost_guard command does not start with Darwin gate:\n"
                        f"Expected to start with: {darwin_gate}\n"
                        f"Got: {command}"
                    )

        self.assertTrue(found_ci_cost_guard,
                        "No ci_cost_guard command found in PreToolUse hooks")


if __name__ == '__main__':
    unittest.main()
