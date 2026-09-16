#!/usr/bin/env python3
"""What park_before_toss_guard SAYS when it refuses a large discard (CE-12.13).

Background: the refusal's text at HEAD claimed "nothing you can type will"
clear the block. That is false -- the guard has a launch-shell path that
does clear it, and fixtures 02 and 03 in
`.claude/hooks/tests/park_before_toss_guard/` pin both of its spellings as
PASS. This test asserts the refusal keeps every true sentence (parking does
not clear the block, the park-work.sh line, "fix this guard, or report it
and stop") while dropping the false one, and that the message still names
no environment variable and no magic comment (CE-12.2, AC3 -- the mechanism
itself stays unnamed).

Modelled on tests/test_shared_rules_link_guard_message.py: build a
temporary git repository, feed the hook a PreToolUse Bash payload through
subprocess, assert the exit code, and read its stderr.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "park_before_toss_guard.py")


def _git(args, cwd):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True,
                    capture_output=True, text=True)


class TestTheRefusalSaysOnlyWhatIsTrue(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", self.base], check=False))

        self.repo = os.path.join(self.base, "repo")
        os.makedirs(self.repo)
        _git(["init", "-q"], self.repo)
        _git(["config", "user.email", "test@example.com"], self.repo)
        _git(["config", "user.name", "Test"], self.repo)
        with open(os.path.join(self.repo, "README.md"), "w") as fh:
            fh.write("baseline\n")
        _git(["add", "README.md"], self.repo)
        _git(["commit", "-q", "-m", "baseline"], self.repo)

    def refuse(self, command):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": command},
                              "cwd": self.repo})
        p = subprocess.run([sys.executable, HOOK], input=payload,
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 2, p.stderr)
        return p.stderr

    def test_the_refusal_claims_nothing_the_guard_itself_disproves(self):
        # Same shape as fixture 01: a large untracked file + `git clean -fd`,
        # which the guard's own fixture suite pins as BLOCK.
        with open(os.path.join(self.repo, "bigfile.txt"), "w") as fh:
            fh.write("\n".join(str(n) for n in range(1, 201)) + "\n")

        stderr = self.refuse("git clean -fd")

        # The false claim is gone: the refusal does not say that nothing a
        # reader can type clears the block.
        self.assertNotIn("nothing you can type", stderr, stderr)

        # The true sentences survive.
        self.assertIn("Parking does NOT clear this block", stderr)
        self.assertIn("park-work.sh", stderr)
        self.assertIn("fix this guard", stderr)
        self.assertIn("report it and stop", stderr)

        # The mechanism that DOES clear the block stays unnamed (CE-12.2,
        # AC3): no environment-variable-shaped token, no magic-comment
        # marker.
        self.assertIsNone(re.search(r"[A-Z][A-Z0-9_]{3,}_OK", stderr), stderr)
        self.assertIsNone(re.search(r"<!--.*OK", stderr), stderr)


if __name__ == "__main__":
    unittest.main()
