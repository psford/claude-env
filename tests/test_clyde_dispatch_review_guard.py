#!/usr/bin/env python3
"""clyde_dispatch_review_guard reads what a shell will actually run (CE-2.43).

Refiles CE-2.28. QA found this judging CE-12.7: the gate works on the command
Patrick sees, not on a command wearing a costume. Reproduced 2026-09-15 by
feeding these three payloads to the live guard at HEAD (9a5f83c): a dispatch
carried inside `bash -c`, and one whose role token follows `--ticket`, both
passed with no dialog; a dispatch that is only TEXT (an echoed line, a
heredoc body) raised one anyway.

Why this file exists rather than the exit-code fixture driver: this guard's
two decisions are silent-allow (exit 0, nothing on stdout) and ask (exit 0,
JSON on stdout naming permissionDecision "ask"). Both exit 0. A driver that
compares exit codes cannot tell "reviewed" from "rubber-stamped" -- these are
unit tests for exactly that reason (CE-2.36 answer A).

Every dispatch-shaped string here lives in this file, never in a shell
command typed at the harness -- the live session runs this same guard, and a
dispatch-shaped Bash command raises a real approval dialog on Patrick's
screen even inside `echo` or `grep`.
"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "clyde_dispatch_review_guard.py")


def _decision(command):
    """The hook's permissionDecision for `command`, or None if it stayed silent.

    Silent (no stdout, exit 0) is the guard's "not a dispatch, allow" answer.
    "ask" on stdout is the guard's "Patrick must see this" answer. Both exit
    0, which is the whole reason this is a unit test rather than a fixture.
    """
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
    })
    result = subprocess.run([sys.executable, HOOK], input=payload,
                            capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        return None
    out = json.loads(result.stdout)
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


class TestTheGateSeesTheDispatch(unittest.TestCase):
    def test_a_dispatch_inside_an_interpreter_is_asked(self):
        """`bash -c` runs its payload exactly as though it had been typed at
        the prompt directly. A gate that stops reading at the word `bash`
        never sees the dispatch sitting inside it -- true whichever quote
        style wraps the payload (CE-2.43 AC1)."""
        single_quoted = (
            "bash -c 'glm-agent clyde haiku "
            "\"Check AC1 on CE-2.43 by running its tests\"'"
        )
        double_quoted = (
            'bash -c "glm-agent clyde haiku '
            "'Check AC1 on CE-2.43 by running its tests'\""
        )
        self.assertEqual(
            "ask", _decision(single_quoted),
            "a single-quoted dispatch inside bash -c was not asked")
        self.assertEqual(
            "ask", _decision(double_quoted),
            "a double-quoted dispatch inside bash -c was not asked")

    def test_a_role_after_a_flag_value_is_asked(self):
        """`--ticket` consumes the token after it. A scan that treats every
        non-dash token as a candidate role reads that value as the role
        instead, and never notices the real `clyde` two tokens later
        (CE-2.43 AC2)."""
        command = ('glm-agent --ticket CE-2.43 clyde haiku '
                   '"Check AC2 on CE-2.43 by running its tests"')
        self.assertEqual("ask", _decision(command))

    def test_a_dispatch_that_is_only_text_is_not_asked(self):
        """A dispatch that is only TEXT -- an echoed line, a heredoc body
        nothing executes -- describes a dispatch; it does not run one. A
        plain dispatch alongside both still asks, so the fix for the false
        allow does not become a blanket false ask (CE-2.43 AC3)."""
        echoed = ('echo glm-agent clyde haiku '
                  '"would run this, but this line only prints it"')
        heredoc_body = (
            "cat <<'EOF'\n"
            "reminder: do not run glm-agent clyde haiku by hand, use the "
            "wrapper script instead\n"
            "EOF"
        )
        plain_dispatch = ('glm-agent clyde haiku '
                          '"Check AC3 on CE-2.43 by running its tests"')

        self.assertIsNone(
            _decision(echoed),
            "a dispatch line printed by echo was read as a real dispatch")
        self.assertIsNone(
            _decision(heredoc_body),
            "a dispatch line inside a heredoc body was read as a real "
            "dispatch")
        self.assertEqual(
            "ask", _decision(plain_dispatch),
            "a plain, unwrapped dispatch stopped being asked")


if __name__ == "__main__":
    unittest.main()
