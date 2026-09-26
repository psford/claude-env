#!/usr/bin/env python3
"""visual_ac_manual_guard exempts two exact spans, and nothing else (CE-2.85).

The CSO's list review of 2026-09-25 (reviews/2026-09-25-ce285-list-infosec.md)
chose option A1: leave `appears` and `ui` in the unconditional tier, and mask
only two spans before judging:
- `appears` where a stream follows it ("appears on stderr");
- `ui` inside the harness's hook order ("bash, watch, pr, commit, scope, ui").

These tests pin its finding-1 table through the hook's real stdin contract.
CH-281.1's drafted criteria 3 and 4, refused before this change, pass; every
other use of the two words is refused exactly as before; and the mask covers
the span, not the word (finding 4).
"""
import json
import os
import shlex
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "visual_ac_manual_guard.py")

# CH-281.1's drafted criteria, verbatim from
# ~/.local/share/harness/ch2811-criteria-draft.md.
CRITERION_3 = (
    "The commands in test_hooks.py TestAContinuationDoesNotHideAReservedCommand"
    ".CASES and .WRAPPED plus the commit-then-handoff command, run with no watch"
    " heartbeat and each sent with and without the payload cwd -> the fused"
    " entry refuses exactly when at least one of the six standalone hooks"
    " refuses, and its reason is the one the first refuser gives alone, in the"
    " order bash, watch, pr, commit, scope, ui."
)
CRITERION_4 = (
    "A refusal is exit 2 with exactly one JSON deny object on stdout, carrying"
    " the refusing check's text, which also appears on stderr."
)


def hook_exit(text):
    """The hook's exit code for `ticket ac add` of `text` as automated."""
    command = (f"ticket ac add CH-281.1 --kind automated --text {shlex.quote(text)}"
               " --by tests/test_x.py::T::t")
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True, text=True, timeout=30)
    return proc.returncode


class TestTheExemptSpans(unittest.TestCase):

    def test_the_two_real_ch281_criteria_file_as_automated(self):
        self.assertEqual(hook_exit(CRITERION_3), 0)
        self.assertEqual(hook_exit(CRITERION_4), 0)

    def test_a_visual_word_outside_the_exempt_spans_is_still_refused(self):
        for text in (
            "the banner appears after the test loads",      # F1: loose anchor
            "the UI lists each file",                       # F2: loose anchor
            "the banner appears after the command exits",   # cmd-exits
            "the banner appears",                           # no anchor
            "the ui is ready",                              # no anchor
            "the page renders and the text appears on stderr",  # another strong word
        ):
            with self.subTest(text=text):
                self.assertEqual(hook_exit(text), 2)

    def test_the_exemption_masks_the_span_not_the_word(self):
        self.assertEqual(
            hook_exit("the banner appears on the page and appears on stderr"), 2)


if __name__ == "__main__":
    unittest.main()
