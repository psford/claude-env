#!/usr/bin/env python3
"""cap_task_timeout rewrites the call rather than refusing it.

It is one of the hooks that runs and had never been watched work. It also does
not belong in the "can refuse" count: it emits permissionDecision "allow" with
an updatedInput, and has no exit-2 path at all. A guard that silently rewrites
your arguments is arguably more worth testing than one that refuses, because a
refusal is visible and a rewrite is not.

The property: no TaskOutput call can block the session indefinitely.

Fixtures cannot express this. The runner asks PASS/BLOCK (an exit code) and the
advisory driver asks FIRES/SILENT (did it speak) -- neither reads updatedInput,
which is the only place the behaviour shows up. Hence a Python test.

Run: python3 .claude/hooks/tests/test_cap_task_timeout.py
"""

import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "cap_task_timeout.py")
CAP = 60000


def run(tool_input, tool_name="TaskOutput"):
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    done = subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, timeout=15)
    out = {}
    if done.stdout.strip():
        out = json.loads(done.stdout)
    return done.returncode, (out.get("hookSpecificOutput") or {})


class TestTheCap(unittest.TestCase):
    def test_an_over_long_timeout_is_capped(self):
        rc, spec = run({"timeout": 999999, "block": True})
        self.assertEqual(rc, 0)
        self.assertEqual(spec.get("updatedInput", {}).get("timeout"), CAP)

    def test_a_blocking_call_with_no_timeout_gets_one(self):
        """The case that actually hangs a session: block=True and no timeout."""
        rc, spec = run({"block": True})
        self.assertEqual(rc, 0)
        self.assertEqual(spec.get("updatedInput", {}).get("timeout"), CAP)

    def test_block_defaults_to_true_when_absent(self):
        """An omitted `block` must be read as blocking. Reading it as False is
        how the one dangerous shape would slip through untouched."""
        rc, spec = run({})
        self.assertEqual(spec.get("updatedInput", {}).get("timeout"), CAP)

    def test_a_reasonable_timeout_is_left_alone(self):
        rc, spec = run({"timeout": 5000, "block": True})
        self.assertEqual(rc, 0)
        self.assertNotEqual(spec.get("updatedInput", {}).get("timeout"), CAP,
                            "rewrote a timeout that was already fine")

    def test_it_never_refuses(self):
        """It has no exit-2 path, and should not grow one by accident: a
        PreToolUse hook that refuses TaskOutput would strand a running agent."""
        for tool_input in ({"timeout": 999999}, {"block": True}, {}, {"timeout": 1}):
            rc, spec = run(tool_input)
            self.assertEqual(rc, 0, tool_input)
            self.assertIn(spec.get("permissionDecision"), ("allow", None), tool_input)

    def test_the_cap_is_the_documented_one(self):
        """Guards against the constant drifting away from what the docstring and
        the message both promise."""
        src = open(HOOK).read()
        self.assertIn("MAX_TIMEOUT_MS = 60000", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
