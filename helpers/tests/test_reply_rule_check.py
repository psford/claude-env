#!/usr/bin/env python3
"""Tests for helpers/reply_rule_check.py (CE-2.55).

Every test injects a fake Jev client -- the seam TypeSafeClient.ask sits
behind -- so nothing here ever opens a socket or reads a key. The fixtures
are copies of real memory files and a real violating reply from the session
transcript of 2026-09-21, not invented shapes.

Run: python3 helpers/tests/test_reply_rule_check.py
"""

import json
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

    def __init__(self, scores_by_rule):
        self.scores_by_rule = scores_by_rule
        self.calls = []

    def ask(self, state, questions):
        self.calls.append({"state": state, "questions": questions})
        keys = sorted(questions, key=lambda q: int(q[1:]))
        return {qid: self.scores_by_rule(questions[qid], state) for qid in keys}


def noul_instructions(q):
    return q["instructions"]


# The real violating reply, verbatim from the 2026-09-21 session transcript:
# asks Patrick to choose between options in chat, ends on a question, no
# `ticket ask`. This is the feedback_ask_on_the_board_and_wait violation.
VIOLATING_REPLY = """Three tickets filed, all `draft`:

- **CE-2.50** — a dev worktree doesn't inherit the shared rules until a commit is refused
- **CH-224.96** — `glm-agent` resolves `--commit` against the wrong repo when the caller has no `.env`
- **CH-224.97** — `ac add --kind automated` accepts no test and it surfaces at your accept

CE-2.49 is `in_review`, QA-passed, with AC2 and AC3 verified. AC1 is the one you said not to refile — it's still unverified and will refuse your accept.

Want me to leave AC1 as-is for you to decide on, or is there a resolution you'd take?"""


class ReplyRuleCheckTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Fixture memory dir: a trimmed copy of the live store's shape, with
        # the real ask_on_the_board memory copied whole so the "How to apply"
        # text quoted in a block is the real one.
        self.memory_dir = Path(self.tmp) / "memory"
        self.memory_dir.mkdir()
        (self.memory_dir / "feedback_ask_on_the_board_and_wait.md").write_text(
            ASK_ON_THE_BOARD_MEMORY, encoding="utf-8")
        self.rules = reply_rule_check.load_rules(self.memory_dir)
        self.assertEqual(len(self.rules), 1)
        self.baseline_file = Path(self.tmp) / "base.json"
        self.baseline_file.write_text(json.dumps({
            "_meta": {"replies_fitted": 24},
            "rules": {"feedback_ask_on_the_board_and_wait": {
                "mean": 0.1, "max": 0.1, "n": 24}},
        }))
        self.baselines = json.loads(self.baseline_file.read_text())["rules"]

    def check(self, text, client):
        return reply_rule_check.check_reply(
            text, memory_dir=self.memory_dir, client=client,
            base_rates=self.baselines)


class TestABrokenRuleBlocks(ReplyRuleCheckTestCase):
    """AC1: a reply that breaks a saved feedback rule is blocked, and the
    block names the rule it broke and quotes that rule's instruction."""

    def test_a_reply_asking_patrick_in_chat_is_blocked_naming_the_rule(self):
        client = FakeClient(lambda q, state: 0.9 if "board" in q["instructions"]
                            else 0.1)
        fired = self.check(VIOLATING_REPLY, client)
        self.assertEqual(len(fired), 1, f"exactly one rule fires: {fired}")
        f = fired[0]
        self.assertEqual(f["key"], "feedback_ask_on_the_board_and_wait")
        # The verdict names the rule...
        self.assertIn("ask_on_the_board", f["key"])
        # ...and carries the rule's own instruction, so the fix is obvious:
        # the How to apply bullets from the memory file, verbatim.
        self.assertIn("`ticket ask <ID> --question", f["how_to_apply"])
        self.assertIn("STOP", f["how_to_apply"])
        self.assertGreaterEqual(f["score"], reply_rule_check.FIRE_FLOOR)
        # And it was one batched call carrying every rule, not one per rule.
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(client.calls[0]["questions"]), len(self.rules))
        self.assertIn("Want me to leave AC1", client.calls[0]["state"]["reply"])


class TestAcceptedRepliesPass(ReplyRuleCheckTestCase):
    """AC2: a reply Patrick accepted is not blocked -- rules that fire on
    every reply are calibrated out against replies he accepted."""

    def test_accepted_replies_raise_no_block(self):
        # A rule that reads as violated by ANY prose scores 0.88 here too --
        # but it scored exactly this on the replies the baselines were fitted
        # from (max 0.88 in the fixture baseline file), so the calibration
        # subtracts it out and an accepted reply stays quiet.
        self.baselines["feedback_ask_on_the_board_and_wait"] = {
            "mean": 0.8, "max": 0.88, "n": 24}
        client = FakeClient(lambda q, state: 0.88)
        # An ordinary accepted reply: findings and a recommendation, ending
        # without a question to Patrick.
        accepted = (
            "CE-2.50 is merged and develop is green across both suites. "
            "The worktree now inherits the shared rules at creation time, "
            "so the first commit is no longer where a missing symlink "
            "surfaces.\n\nRecommendation: merge develop to main before the "
            "next story starts, so new worktrees branch from a trunk that "
            "already carries the fix.")
        fired = self.check(accepted, client)
        self.assertEqual(fired, [], "an accepted reply must raise no block")

        # Sanity that the same score WOULD fire without the calibration:
        # drop the baseline to zero and the rule is above the floor again.
        self.baselines["feedback_ask_on_the_board_and_wait"] = {
            "mean": 0.0, "max": 0.0, "n": 24}
        fired = self.check(accepted, client)
        self.assertEqual(len(fired), 1,
                         "the calibration, not the score, is what keeps "
                         "an accepted reply quiet")


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
