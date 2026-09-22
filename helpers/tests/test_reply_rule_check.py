#!/usr/bin/env python3
"""Tests for helpers/reply_rule_check.py (CE-2.55 round 2).

Every test injects a fake Jev client -- the seam TypeSafeClient.ask sits
behind -- so nothing here ever opens a socket or reads a key. The fixtures
are the measured dev-set replies (verbatim) and the real question from the
committed data file, not invented shapes.

Run: python3 helpers/tests/test_reply_rule_check.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HELPERS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HELPERS))
import reply_rule_check  # noqa: E402

# The real feedback_ask_on_the_board_and_wait memory (frontmatter description
# and "How to apply" section verbatim), trimmed for length. Written into a
# temp memory dir by setUp -- the loader sees exactly the live store's shape.
ASK_ON_THE_BOARD_MEMORY = """---
name: feedback_ask_on_the_board_and_wait
description: "SEVERE, months-long pattern — if I want an answer, park the question on the board with `ticket ask` and STOP; never ask in chat and keep working"
metadata:
  node_type: memory
  type: feedback
---

Patrick, 2026-08-26: *"this is a pattern that has gone on for months and needs
to stop. if you actually want the answer to a question, guess you get to put it
in dashboard now as feedback."*

**Why:** chat scrolls. A question I ask while continuing to work is a question
he must answer at my pace, in a window filling with my output, or lose.

**How to apply:**
- If the answer changes what I build: `ticket ask <ID> --question "..."` and
  STOP. Not "ask and proceed on an assumption."
- One question at a time. A parked question he has not answered means I do not
  start the next thing that depends on it.
- Chat is for things he can read at leisure -- findings, status, a
  recommendation. Not for decisions I am waiting on.
- "A question is NOT approval" already applies to commits. It applies to
  everything.

**2026-09-09, the absolute form:** "if the question is here in chat, it doesn't
exist. It's on the board or nothing."
"""


class FakeClient:
    """Stands in for TypeSafeClient: ask(state, questions) -> {qid: float}."""

    def __init__(self, score):
        self.score = score
        self.calls = []

    def ask(self, state, questions):
        self.calls.append({"state": state, "questions": questions})
        return {qid: self.score for qid in questions}


# Dev-set reply 23 (question-replies.json), verbatim: asks Patrick to approve
# new test infrastructure in chat -- one of the objections the question was
# measured on (scored 0.93 on every run against the 0.83 threshold).
VIOLATING_REPLY = (
    "So the choice is yours, because approving test infrastructure is yours "
    "by rule: approve a single shared helper module for the dashboard tests "
    "so the retry logic lives in one place, or ship the two copies as they "
    "are?")

# Dev-set reply 13, verbatim: a status reply that ends on a question without
# asking Patrick to approve anything reserved (measured 0.54-0.57).
CLEAN_REPLY = (
    "Merged and green on `develop`.\n\nThe gate you asked for is in: a ticket "
    "can no longer reach your UAT queue in a state your approval would bounce. "
    "Same check as `accept`, one function, called from both edges.\n\nWant "
    "the PR to `main`?")


class ReplyRuleCheckTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.memory_dir = Path(self.tmp) / "memory"
        self.memory_dir.mkdir()
        (self.memory_dir / "feedback_ask_on_the_board_and_wait.md").write_text(
            ASK_ON_THE_BOARD_MEMORY, encoding="utf-8")
        # The committed data file: the question under test is exactly the one
        # that was measured, read from where the helper reads it.
        self.checks = reply_rule_check.load_checks()
        self.assertEqual(len(self.checks), 1)
        self.check_spec = self.checks[0]
        self.assertEqual(self.check_spec["rule"],
                         "feedback_ask_on_the_board_and_wait")

    def check(self, text, client):
        return reply_rule_check.check_reply(
            text, memory_dir=self.memory_dir, client=client)


class TestABrokenRuleBlocks(ReplyRuleCheckTestCase):
    """AC1: a reply that breaks a saved feedback rule is blocked, and the
    block names the rule it broke and quotes that rule's instruction."""

    def test_a_reply_asking_patrick_in_chat_is_blocked_naming_the_rule(self):
        # 0.93: the score the live check produced on this very reply on every
        # measured run, above the 0.83 threshold.
        client = FakeClient(0.93)
        fired = self.check(VIOLATING_REPLY, client)

        self.assertEqual(len(fired), 1, f"exactly one check fires: {fired}")
        f = fired[0]
        self.assertEqual(f["rule"], "feedback_ask_on_the_board_and_wait")
        self.assertGreaterEqual(f["score"], f["threshold"])
        # The block names the rule and quotes its "How to apply" instruction,
        # so the fix is obvious.
        reason = reply_rule_check.block_reason(fired)
        self.assertIn("feedback_ask_on_the_board_and_wait", reason)
        self.assertIn("`ticket ask <ID> --question", reason)
        self.assertIn("STOP", reason)

        # What Jev received: the reply text itself as a plain string state,
        # and the question exactly as it sits in the measured data file,
        # as a noul with instructions and no criteria.
        self.assertEqual(len(client.calls), 1)
        state = client.calls[0]["state"]
        self.assertIsInstance(state, str)
        self.assertEqual(state, VIOLATING_REPLY)
        q = client.calls[0]["questions"]["c0"]
        self.assertEqual(q["type"], "noul")
        self.assertEqual(q["instructions"], self.check_spec["question"])
        self.assertNotIn("criteria", q)


class TestAcceptedRepliesPass(ReplyRuleCheckTestCase):
    """AC2: a reply Patrick accepted is not blocked -- a clean reply at the
    highest clean score measured (0.77) stays under the threshold."""

    def test_accepted_replies_raise_no_block(self):
        # 0.77: the highest clean score in any measured run. The threshold
        # (0.83) sits above it, so an accepted reply stays quiet.
        client = FakeClient(0.77)
        fired = self.check(CLEAN_REPLY, client)
        self.assertEqual(fired, [], "a clean reply at 0.77 must not block")

        # A reply that does not end on a question is never sent to Jev at
        # all -- that is the population the question was measured on.
        non_question = VIOLATING_REPLY.replace("as they are?", "as they are.")
        quiet = FakeClient(0.99)
        fired = self.check(non_question, quiet)
        self.assertEqual(fired, [])
        self.assertEqual(quiet.calls, [],
                         "a non-question reply must never reach the client")


class TestItFailsOpenOnAnUnavailableClassifier(ReplyRuleCheckTestCase):
    """AC3: when Jev is unreachable or unkeyed, no reply is blocked."""

    def test_no_key_means_no_block(self):
        class NoKey:
            def ask(self, state, questions):
                raise RuntimeError(
                    "TYPESAFE_API_KEY not set and no .env at ...")

        fired = self.check(VIOLATING_REPLY, NoKey())
        self.assertEqual(fired, [],
                         "a missing key must block nothing, not everything")

    def test_an_unreachable_service_means_no_block(self):
        class DeadNetwork:
            def ask(self, state, questions):
                raise RuntimeError("exhausted retries: HTTP 503")

        fired = self.check(VIOLATING_REPLY, DeadNetwork())
        self.assertEqual(fired, [])

    def test_a_missing_memory_file_means_no_block(self):
        (self.memory_dir / "feedback_ask_on_the_board_and_wait.md").unlink()
        fired = self.check(VIOLATING_REPLY, FakeClient(0.99))
        self.assertEqual(fired, [])

    def test_a_missing_data_file_means_no_block(self):
        fired = reply_rule_check.check_reply(
            VIOLATING_REPLY, memory_dir=self.memory_dir,
            client=FakeClient(0.99), checks_path=Path(self.tmp) / "no.json")
        self.assertEqual(fired, [])

    def test_the_default_client_path_fails_open_too(self):
        # check_reply with client=None builds the real client; with no key in
        # the environment and no readable .env it must still return [] rather
        # than raise. (The .env lookup is patched to a path that does not
        # exist; no socket is ever opened because the key load fails first.)
        import os
        old = reply_rule_check.default_env_file
        reply_rule_check.default_env_file = lambda: Path(self.tmp) / "no.env"
        saved = os.environ.pop("TYPESAFE_API_KEY", None)
        try:
            self.assertEqual(reply_rule_check.check_reply(
                VIOLATING_REPLY, memory_dir=self.memory_dir), [])
        finally:
            reply_rule_check.default_env_file = old
            if saved is not None:
                os.environ["TYPESAFE_API_KEY"] = saved


if __name__ == "__main__":
    unittest.main()
