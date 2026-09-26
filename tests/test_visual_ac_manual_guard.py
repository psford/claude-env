#!/usr/bin/env python3
"""visual_ac_manual_guard exempts three exact spans, and nothing else.

CE-2.85 added the first two; CE-2.89 added the third, `ui` as the stem of
`ui.md` (TestTheSpecFileSpan, below).

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


# CH-291.10's two drafted criteria, verbatim from the command the hook refused
# on 2026-09-26 (CE-2.89's description). They name the spec file ui.md.
CH2910_CRITERION_1 = (
    "Every ## section of the committed spec corpus, api-design.md and ui.md"
    " included, states its rule on a **Rule:** line"
)
CH2910_CRITERION_2 = (
    "No line of the committed spec corpus, api-design.md and ui.md included,"
    " uses the word the plan's Phase 3 extraction keys on"
)


class TestTheSpecFileSpan(unittest.TestCase):
    """CE-2.89: `ui` is masked only as the stem of `ui.md`.

    Option B1 of the CSO's list review of 2026-09-26
    (reviews/2026-09-26-ce289-list-infosec.md). Every other use of the word
    stays refused, including any other extension after it: the review's
    finding 1 rejected an open `ui.<ext>` span, because an invented extension
    would both mask the word and supply its own anchor. The inputs are the
    review's, with its corrections to the list's G5 and G6 rows.
    """

    def test_the_two_ch2910_criteria_file_as_automated(self):
        self.assertEqual(hook_exit(CH2910_CRITERION_1), 0)
        self.assertEqual(hook_exit(CH2910_CRITERION_2), 0)

    def test_every_other_use_is_still_refused(self):
        for text in (
            "the ui lists each file",           # G4: bare, with a loose anchor
            "the UI shows the banner",          # G4: bare, with an ambiguous word
            "ui.md renders the table",          # G3: a strong word beside the span
            "ui.mdx and ui.md5 stay judged",    # no word boundary after md
            "the ui.mode shows the banner",     # G6 as corrected: an invented extension
            "ui.css shows the hover state",     # G5 as corrected
            "ui.tsx shows the panel",           # B2's extension, not B1's
            "the ui .md split",                 # a space breaks the file name
        ):
            with self.subTest(text=text):
                self.assertEqual(hook_exit(text), 2)

    def test_every_spelling_of_the_file_name_is_masked(self):
        for text in (
            "`ui.md` anchors the rule",                              # backticked
            "the corpus includes specs/ui.md and its Rule: lines",  # under a path
            "see the anchor at specs/ui.md#overview",               # with an anchor
            "UI.md carries the rule",                                # upper case
            "the rule lives in ui.md",                               # end of the text
            "the section starts at ui.md:12",                        # a line number
        ):
            with self.subTest(text=text):
                self.assertEqual(hook_exit(text), 0)

    def test_the_mask_covers_the_span_not_the_word(self):
        self.assertEqual(hook_exit("ui.md says the ui is blue"), 2)


if __name__ == "__main__":
    unittest.main()
