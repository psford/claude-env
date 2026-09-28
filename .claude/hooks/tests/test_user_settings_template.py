#!/usr/bin/env python3
"""Test the hook wirings in infrastructure/claude-settings/user-settings.json.

CE-25.1: ci_cost_guard wirings are gated to Darwin, since iOS builds only work on
macOS. The shared template is installed on non-Darwin hosts and a reinstall
would bring ci_cost_guard back if the gate is not in the template itself.

CE-2.83: no wiring masks a missing hook file. A `test -f <path> || exit 0;`
prefix turned a missing guard into a silent pass, so a checkout without the
claude-env sibling, or a renamed hook, ran nothing and said nothing.

CE-2.108 narrows that rule to its intent, after CE-2.100's reviewed wiring:
- A guard (PreToolUse or PostToolUse, not advisory) carries no existence
  test at all. Its pinned interpreter exits 2 on a missing file.
- SessionStart, Stop and advisory hooks may test for the file, but only in
  the loud form `test -f <hook> || { echo '<hook> NOT run: ...' >&2; exit 1; }`.
  Exit 2 there does not gate (SessionStart) or loops the turn (Stop). The
  CSO's list review of CE-2.100, answer 1.
- No existence test ever ends in `exit 0`.

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
# The one accepted shape: an existence test whose failure prints NOT run and
# exits 1. Anything else after `test -f <path> ||` is a silent skip.
LOUD_SKIP = re.compile(r"test -f \S+ \|\| \{ echo '[^']*NOT run[^']*' >&2; exit 1; \}")
SILENT_SKIP = re.compile(r"(?:test -f|\[ -f)[^;|]*\|\|\s*exit 0")
GUARD_EVENTS = ("PreToolUse", "PostToolUse")
ADVISORY = ("memory_scan_hook", "detect-orphan-installs")


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
    """CE-2.83, narrowed by CE-2.108: a missing hook file is never a silent pass."""

    def setUp(self):
        with open(TEMPLATE_PATH, 'r') as f:
            self.settings = json.load(f)

    def _commands(self):
        for event in ("PreToolUse", "PostToolUse", "SessionStart", "Stop"):
            for hook_group in self.settings.get("hooks", {}).get(event, []):
                for hook in hook_group.get("hooks", []):
                    yield event, hook.get("command", "")

    def test_no_wiring_masks_a_missing_hook_file(self):
        """No existence test ends in `exit 0`; a guard carries none at all;
        any other existence test is the loud NOT-run form."""
        found = 0
        for event, command in self._commands():
            found += 1
            with self.subTest(event=event, command=command):
                self.assertIsNone(SILENT_SKIP.search(command),
                                  f"{event} wiring passes silently when its hook file is missing")
                if not EXISTENCE_TEST.search(command):
                    continue
                guard = event in GUARD_EVENTS and not any(a in command for a in ADVISORY)
                self.assertFalse(guard, f"{event} guard tests for its hook file; "
                                        "its pinned interpreter must exit 2 instead")
                self.assertRegex(command, LOUD_SKIP,
                                 "an existence test must print NOT run and exit 1")

        # Guard against a vacuous pass: if the template's shape changes and
        # the walk above stops finding hooks, this must fail, not pass.
        self.assertGreater(found, 0, "No hook wiring found in the template")

    def test_the_old_silent_form_is_refused(self):
        """The rule fails on the shape CE-2.83 removed, so it can fail at all."""
        silent = "test -f /x/guard.py || exit 0; /usr/bin/python3 /x/guard.py"
        self.assertIsNotNone(SILENT_SKIP.search(silent))
        loud = ("test -x /usr/bin/python3 || { echo 'g.py NOT run: /usr/bin/python3 missing' >&2; "
                "exit 1; }; test -f /x/g.py || { echo 'g.py NOT run: hook file missing' >&2; "
                "exit 1; }; /usr/bin/python3 /x/g.py")
        self.assertIsNone(SILENT_SKIP.search(loud))
        self.assertRegex(loud, LOUD_SKIP)


if __name__ == '__main__':
    unittest.main()
