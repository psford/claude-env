#!/usr/bin/env python3
"""Run every documented evasion against the guards that claim to stop it.

The CH-8 retrospective found that each guard bug this session followed one shape:
an evasion was thought of only *after* it had already been used, a test was added
for that one form, and nothing accumulated. This is the accumulator.

What it asserts is deliberately not "the regex catches it". A text guard reading a
shell command string cannot catch `eval`, and demanding that restarts the arms
race the retrospective concluded against. It asserts that the corpus's record of
which layer stops each form is still TRUE -- so a form that regresses from
`text` to `none` fails, and a form recorded as `none` is a documented hole rather
than a surprise.

Run: python3 .claude/hooks/tests/test_bypass_corpus.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CORPUS = os.path.join(REPO, "shared", "bypass-corpus.json")
HOOKS = os.path.abspath(os.path.join(HERE, ".."))
MAIN_GUARD = os.path.join(HOOKS, "main_branch_guard.py")

# Which layer each family is checked against here. `server` is not testable from
# a workstation without pushing, so those entries are asserted as documentation
# only -- and that limit is stated rather than quietly skipped.
TEXT_LAYER_FAMILIES = ("commit_on_main", "destructive", "false_positive")


def load_corpus():
    """The corpus, or a hard failure.

    Not a skip. A suite that silently passes because its input file is missing is
    the "Skipping X -- not installed" masquerade: it exits 0 and proves nothing.
    """
    if not os.path.exists(CORPUS):
        raise SystemExit(
            f"bypass corpus not found at {CORPUS}.\n"
            "This suite cannot pass without it. It is not optional and it does not skip."
        )
    with open(CORPUS) as fh:
        return json.load(fh)


def scratch_repo_on(branch):
    """A throwaway repo whose HEAD sits on `branch`."""
    path = tempfile.mkdtemp()
    run = lambda *a: subprocess.run(["git", *a], cwd=path, check=True,  # noqa: E731
                                    capture_output=True)
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    run("commit", "-q", "--allow-empty", "-m", "init")
    run("branch", "-M", branch)
    return path


def ask_text_guard(command, cwd):
    """What the PreToolUse text guard says about this command. True = blocked."""
    r = subprocess.run(
        [sys.executable, MAIN_GUARD],
        input=json.dumps({"tool_name": "Bash", "cwd": cwd,
                          "tool_input": {"command": command}}),
        capture_output=True, text=True, timeout=20)
    return r.returncode != 0


class TestCorpusIsWellFormed(unittest.TestCase):
    # AC1
    def setUp(self):
        self.corpus = load_corpus()

    def test_it_loads_and_has_entries(self):
        self.assertGreater(len(self.corpus["entries"]), 0)

    def test_every_entry_carries_the_fields_that_make_it_useful(self):
        for e in self.corpus["entries"]:
            for field in ("id", "family", "command", "effect",
                          "expect_blocked", "stopped_by"):
                self.assertIn(field, e, f"{e.get('id')} is missing {field}")

    def test_ids_are_unique(self):
        ids = [e["id"] for e in self.corpus["entries"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate corpus id")

    def test_stopped_by_is_a_known_layer(self):
        allowed = {"text", "git_hook", "server", "none", "n/a"}
        for e in self.corpus["entries"]:
            self.assertIn(e["stopped_by"], allowed, e["id"])

    def test_it_contains_forms_that_must_not_be_blocked(self):
        # AC3. A corpus of only true positives would let the fix for one become
        # "block everything", which is how a guard gets disabled.
        false_positives = [e for e in self.corpus["entries"]
                           if e["expect_blocked"] is False]
        self.assertGreater(len(false_positives), 0)


class TestMissingCorpusFailsLoudly(unittest.TestCase):
    # AC4
    def test_a_missing_corpus_raises_rather_than_skipping(self):
        import unittest.mock as mock
        with mock.patch("os.path.exists", return_value=False):
            with self.assertRaises(SystemExit):
                load_corpus()


class TestTextLayerMatchesTheRecord(unittest.TestCase):
    # AC2
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()
        cls.on_main = scratch_repo_on("main")
        cls.on_feature = scratch_repo_on("feature/x")

    @classmethod
    def tearDownClass(cls):
        for p in (cls.on_main, cls.on_feature):
            subprocess.run(["rm", "-r", "--", p], check=False)

    def test_forms_recorded_as_text_stopped_are_still_stopped(self):
        """A regression here means a guard quietly stopped working."""
        regressed = []
        for e in self.corpus["entries"]:
            if e["family"] not in TEXT_LAYER_FAMILIES:
                continue
            if e["stopped_by"] != "text":
                continue
            if not ask_text_guard(e["command"], self.on_main):
                regressed.append(e["id"])
        self.assertEqual(regressed, [],
                         f"forms recorded as caught by the text layer are no longer caught: {regressed}")

    def test_forms_that_must_not_be_blocked_are_not_blocked(self):
        """AC3 in anger. Every one of these was a real false positive."""
        wrongly_blocked = []
        for e in self.corpus["entries"]:
            if e["expect_blocked"] is not False:
                continue
            # False positives are judged on a feature branch: that is where
            # ordinary work happens, and blocking it there is the damage.
            if ask_text_guard(e["command"], self.on_feature):
                wrongly_blocked.append(e["id"])
        self.assertEqual(wrongly_blocked, [],
                         f"legitimate commands refused: {wrongly_blocked}")

    def test_the_record_of_unstopped_forms_is_honest(self):
        """A form recorded as `none` must genuinely not be stopped.

        If one silently started being caught, the record is stale and the corpus
        is lying in the safe direction -- which still makes it untrustworthy.
        """
        stale = []
        for e in self.corpus["entries"]:
            if e["family"] not in ("commit_on_main", "destructive"):
                continue
            if e["stopped_by"] != "none":
                continue
            if ask_text_guard(e["command"], self.on_main):
                stale.append(e["id"])
        self.assertEqual(stale, [],
                         f"corpus says these are unstopped, but the guard caught them "
                         f"-- update stopped_by: {stale}")


class TestWhatThisSuiteCannotCheck(unittest.TestCase):
    def test_server_layer_entries_are_documentation_only(self):
        """Stated, not skipped.

        Entries whose only defence is branch protection cannot be exercised
        without pushing to a real remote. They are recorded so the layering is
        visible, and this test exists so that limit is written down rather than
        discovered later by someone assuming coverage.
        """
        server_only = [e["id"] for e in load_corpus()["entries"]
                       if e["stopped_by"] == "server"]
        self.assertGreater(len(server_only), 0,
                           "expected at least one form defended only server-side")


if __name__ == "__main__":
    unittest.main(verbosity=2)
