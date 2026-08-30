#!/usr/bin/env python3
"""What ci_cost_guard SAYS when it refuses a push (CE-2.8).

Why this file exists rather than another fixture: the fixture harness compares
exit codes only. A control that replaced the entire refusal with a bare
`return 2` passed all nineteen fixtures — so the message was asserted by
nothing, and the message is most of the point.

The old refusal is the reason. It printed:

    CI_MACOS_PUSH_OK=1 git push ...

which cannot work. The guard reads os.environ, and a PreToolUse hook runs in
Claude Code's process, not in the shell where that prefix would apply. So the
only escape it offered was unreachable from the surface it was printed on, and
road-trip could not be pushed at all. A refusal that names an impossible remedy
is worse than one that names none: it sends the reader to spend time on a door
that does not open.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "ci_cost_guard.py")

WORKFLOW = ("on:\n  push:\n    branches: [main]\n"
            "jobs:\n  build:\n    runs-on: macos-15\n")


class TestRefusalMessage(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", self.repo], check=False))
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        wf = os.path.join(self.repo, ".github", "workflows")
        os.makedirs(wf)
        with open(os.path.join(wf, "ios-ci.yml"), "w") as fh:
            fh.write(WORKFLOW)

    def refuse(self):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "git push origin main"},
                              "cwd": self.repo})
        env = {k: v for k, v in os.environ.items() if k != "CI_MACOS_PUSH_OK"}
        p = subprocess.run([sys.executable, HOOK], input=payload,
                           capture_output=True, text=True, env=env, check=False)
        self.assertEqual(p.returncode, 2, p.stderr)
        return p.stderr

    def test_it_names_the_workflow_that_can_fire(self):
        """Without this the reader has to search .github/workflows themselves,
        and in a repo with five workflows that is the whole diagnosis."""
        self.assertIn("ios-ci.yml", self.refuse())

    def test_it_names_both_real_remedies(self):
        """The fix is in the workflow, not in a bypass. Either of these makes
        the push legal and costs nothing."""
        err = self.refuse()
        self.assertIn("workflow_dispatch", err)
        self.assertIn("drop the macOS job", err)

    def test_it_does_not_offer_an_in_command_ack(self):
        """The regression this file exists for. `CI_MACOS_PUSH_OK=1 git push`
        was printed as the way forward and could never work, because the hook
        reads os.environ and cannot see a prefix on the command it is judging.

        Matched on the shape that misleads — the variable immediately followed
        by a command — rather than on the variable name, which the message is
        allowed to mention when it says where the override actually has to go.
        """
        err = self.refuse()
        self.assertNotIn("CI_MACOS_PUSH_OK=1 git", err)
        self.assertNotIn("CI_MACOS_PUSH_OK=1 <command>", err)

    def test_it_says_where_the_override_must_actually_be_set(self):
        """A gate claiming to be unbypassable teaches people to hunt for the
        bypass and stop reading. There IS an override; it belongs to Patrick and
        it only works from the launching shell. Say so."""
        err = self.refuse()
        self.assertIn("CI_MACOS_PUSH_OK", err)
        self.assertIn("LAUNCHES", err)

    def test_it_still_says_ios_belongs_off_github(self):
        """The standing ruling, carried in the message rather than assumed
        known: this is why a push-reachable macOS job is a defect and not a
        preference."""
        self.assertIn("iOS", self.refuse())


if __name__ == "__main__":
    unittest.main()
