#!/usr/bin/env python3
"""Test the hook wirings in infrastructure/claude-settings/user-settings.json.

CE-25.1: ci_cost_guard wirings are gated to Darwin, since iOS builds only work on
macOS. The shared template is installed on non-Darwin hosts and a reinstall
would bring ci_cost_guard back if the gate is not in the template itself.

CE-2.83: no wiring masks a missing hook file. `python3` on a missing script
exits 2, which Claude Code treats as a block; a `test -f <path> || exit 0;`
prefix turned that into a silent pass, so a checkout without the claude-env
sibling, or a renamed hook, ran nothing and said nothing.

Run: python3 .claude/hooks/tests/test_user_settings_template.py
"""
import json
import os
import re
import unittest

# Get the path to infrastructure/claude-settings/user-settings.json
# relative to the .claude/hooks/tests directory
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "infrastructure", "claude-settings",
                              "user-settings.json")

# A file-existence test in front of the hook call: `test -f <path>` or
# `[ -f <path> ]`. The Darwin gate on ci_cost_guard (`[ "$(uname)" = Darwin ]
# || exit 0;`) is a platform gate, not an existence test, and stays.
EXISTENCE_TEST = re.compile(r'\btest -f\b|\[ -f\b')


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


class TestNoSilentSkipOnMissingHookFile(unittest.TestCase):
    """CE-2.83: no python3 hook wiring skips silently when its file is missing."""

    def setUp(self):
        with open(TEMPLATE_PATH, 'r') as f:
            self.settings = json.load(f)

    def test_no_wiring_masks_a_missing_hook_file(self):
        """No python3 command under PreToolUse, PostToolUse, SessionStart or
        Stop tests for its hook file before running it, so a missing file
        blocks (python3 exits 2) instead of passing.
        """
        found_python_hook = 0
        for event in ("PreToolUse", "PostToolUse", "SessionStart", "Stop"):
            for hook_group in self.settings.get("hooks", {}).get(event, []):
                for hook in hook_group.get("hooks", []):
                    command = hook.get("command", "")
                    if "python3" not in command:
                        continue
                    found_python_hook += 1
                    self.assertIsNone(
                        EXISTENCE_TEST.search(command),
                        f"{event} wiring passes silently when its hook file "
                        f"is missing:\n{command}")

        # Guard against a vacuous pass: if the template's shape changes and
        # the walk above stops finding hooks, this must fail, not pass.
        self.assertGreater(found_python_hook, 0,
                           "No python3 hook wiring found in the template")


if __name__ == '__main__':
    unittest.main()
