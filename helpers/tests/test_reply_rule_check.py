#!/usr/bin/env python3
"""Tests for helpers/reply_rule_check.py (CE-2.55 round 2, CE-2.56 round 3).

Every test injects a fake Jev client -- the seam TypeSafeClient.ask sits
behind -- so nothing here ever opens a socket or reads a key. The reply
fixtures are the measured dev-set replies (verbatim); the memory fixture is
a SYNTHETIC note with the same shape as the live one (description line +
"How to apply" list) and no quotation from Patrick.

Run: python3 helpers/tests/test_reply_rule_check.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HELPERS = Path(__file__).resolve().parent.parent
REPO = HELPERS.parent
sys.path.insert(0, str(HELPERS))
import reply_rule_check  # noqa: E402

# The home-path prefix, built by concatenation so this file (which the
# nothing-personal test scans for machine-local literals) never contains it.
HOME_LITERAL = "/ho" + "me/"

# A synthetic memory note with the same SHAPE as the live one -- a
# frontmatter description and a "**How to apply:**" bullet list -- but no
# quotation from Patrick. Written into a temp memory dir by setUp; the
# loader sees exactly the live store's shape.
ASK_ON_THE_BOARD_MEMORY = """---
name: feedback_ask_on_the_board_and_wait
description: "Decisions reserved for the owner go on the board, not in chat"
metadata:
  node_type: memory
  type: feedback
---

A synthetic stand-in for the live feedback note.

**How to apply:**
- If the answer changes what gets built: `ticket ask <ID> --question "..."` and STOP.
- One question at a time; a parked question is not answered by continuing.
- Chat carries findings and recommendations, not decisions being waited on.
"""


class FakeClient:
    """Stands in for TypeSafeClient: ask(state, questions, ...) -> {qid: float}."""

    def __init__(self, score):
        self.score = score
        self.calls = []

    def ask(self, state, questions, retries=None, timeout=None):
        self.calls.append(
            {"state": state, "questions": questions,
             "retries": retries, "timeout": timeout})
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
        return reply_rule_check.check(
            text, memory_dir=self.memory_dir, client=client)


class TestABrokenRuleBlocks(ReplyRuleCheckTestCase):
    """A reply that breaks a saved feedback rule is blocked, and the block
    names the rule it broke and quotes that rule's instruction."""

    def test_a_reply_asking_patrick_in_chat_is_blocked_naming_the_rule(self):
        # 0.93: the score the live check produced on this very reply on every
        # measured run, above the 0.83 threshold.
        client = FakeClient(0.93)
        result = self.check(VIOLATING_REPLY, client)

        self.assertEqual(result["status"], "fired")
        fired = result["fired"]
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

        # What Jev received: the scrubbed reply text itself as a plain
        # string state, and the question exactly as it sits in the measured
        # data file, as a noul with instructions and no criteria.
        self.assertEqual(len(client.calls), 1)
        state = client.calls[0]["state"]
        self.assertIsInstance(state, str)
        self.assertEqual(state, VIOLATING_REPLY)
        q = client.calls[0]["questions"]["c0"]
        self.assertEqual(q["type"], "noul")
        self.assertEqual(q["instructions"], self.check_spec["question"])
        self.assertNotIn("criteria", q)


class TestFormattingCannotSkipTheCheck(ReplyRuleCheckTestCase):
    """AC1: no shape gate. A reserved ask still reaches the classifier when
    the reply does not end on a question -- another line after the question,
    or no question mark at all."""

    def test_a_reply_that_does_not_end_on_a_question_is_still_checked(self):
        for text in (
            # The reserved ask, then an unrelated closing line after it
            # (statement-set reply 98 is this shape, measured 0.94).
            VIOLATING_REPLY.replace("as they are?", "as they are.")
            + "\n\nEither way I will keep the branch green until Monday.",
            # No question mark anywhere at all.
            VIOLATING_REPLY.replace("as they are?", "as they are."),
        ):
            with self.subTest(text=text[-40:]):
                client = FakeClient(0.93)
                result = self.check(text, client)
                self.assertEqual(len(client.calls), 1,
                                 "the reply must reach the classifier")
                self.assertEqual(result["status"], "fired")
                self.assertEqual(result["fired"][0]["rule"],
                                 "feedback_ask_on_the_board_and_wait")


class TestAcceptedRepliesPass(ReplyRuleCheckTestCase):
    """A reply Patrick accepted is not blocked -- a clean reply at the
    highest clean score measured (0.77) stays under the threshold."""

    def test_accepted_replies_raise_no_block(self):
        # 0.77: the highest clean score in any measured run. The threshold
        # (0.83) sits above it, so an accepted reply stays quiet.
        client = FakeClient(0.77)
        result = self.check(CLEAN_REPLY, client)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["fired"], [],
                         "a clean reply at 0.77 must not block")


class TestAnUncheckedReplyIsAnnounced(ReplyRuleCheckTestCase):
    """AC2: when the check cannot run, the reply is not blocked, and the
    session is told the reply went unchecked and why -- never silence."""

    def _assert_unchecked(self, result):
        self.assertEqual(result["status"], "unchecked")
        self.assertEqual(result["fired"], [])
        self.assertTrue(result["reason"].strip(),
                        "an unchecked result carries a plain reason")

    def test_no_key_is_announced_not_silent(self):
        saved = os.environ.pop("TYPESAFE_API_KEY", None)
        old = reply_rule_check.default_env_file
        reply_rule_check.default_env_file = lambda: Path(self.tmp) / "no.env"
        try:
            result = reply_rule_check.check(
                VIOLATING_REPLY, memory_dir=self.memory_dir, client=None)
        finally:
            reply_rule_check.default_env_file = old
            if saved is not None:
                os.environ["TYPESAFE_API_KEY"] = saved
        self._assert_unchecked(result)
        self.assertIn("TYPESAFE_API_KEY", result["reason"])

        # And the hook itself, run as a subprocess with no key reachable,
        # exits 1 with "NOT checked" on stderr and nothing on stdout.
        transcript = Path(self.tmp) / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": VIOLATING_REPLY}]},
        }) + "\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items()
               if k != "TYPESAFE_API_KEY"}
        proc = subprocess.run(
            [sys.executable, str(REPO / ".claude" / "hooks"
                                 / "reply_rule_guard.py")],
            input=json.dumps({"transcript_path": str(transcript)}),
            capture_output=True, text=True, env=env, cwd=str(REPO))
        self.assertEqual(proc.returncode, 1,
                         f"hook stderr: {proc.stderr!r}")
        self.assertIn("NOT checked", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_an_unreadable_or_empty_transcript_is_announced(self):
        # CE-2.57. Both used to reach check() as an empty reply, which is
        # clean -- exit 0 and no notice.
        hook = str(REPO / ".claude" / "hooks" / "reply_rule_guard.py")
        no_text = Path(self.tmp) / "no_text.jsonl"
        no_text.write_text(json.dumps({
            "message": {"role": "user", "content": "hello"},
        }) + "\n", encoding="utf-8")
        for path in (Path(self.tmp) / "missing.jsonl", no_text):
            with self.subTest(transcript=path.name):
                proc = subprocess.run(
                    [sys.executable, hook],
                    input=json.dumps({"transcript_path": str(path)}),
                    capture_output=True, text=True, cwd=str(REPO))
                self.assertEqual(proc.returncode, 1,
                                 f"hook stderr: {proc.stderr!r}")
                self.assertIn("NOT checked", proc.stderr)
                self.assertEqual(proc.stdout, "")

    def test_no_key_means_no_block(self):
        class NoKey:
            def ask(self, state, questions, retries=None, timeout=None):
                raise RuntimeError(
                    "TYPESAFE_API_KEY not set and no .env found")

        result = self.check(VIOLATING_REPLY, NoKey())
        self._assert_unchecked(result)

    def test_an_unreachable_service_is_announced(self):
        class DeadNetwork:
            def ask(self, state, questions, retries=None, timeout=None):
                raise RuntimeError("exhausted retries: HTTP 503")

        self._assert_unchecked(self.check(VIOLATING_REPLY, DeadNetwork()))

    def test_a_missing_memory_file_is_announced(self):
        (self.memory_dir / "feedback_ask_on_the_board_and_wait.md").unlink()
        result = self.check(VIOLATING_REPLY, FakeClient(0.99))
        self._assert_unchecked(result)
        self.assertIn("feedback_ask_on_the_board_and_wait",
                      result["reason"])

    def test_a_missing_data_file_is_announced(self):
        result = reply_rule_check.check(
            VIOLATING_REPLY, memory_dir=self.memory_dir,
            client=FakeClient(0.99), checks_path=Path(self.tmp) / "no.json")
        self._assert_unchecked(result)

    def test_a_non_numeric_answer_is_announced(self):
        # AC2: a classifier answer that is not a probability between 0 and 1
        # is announced as unchecked with the reason -- never silently skipped.
        for bad in (None, "high", 1.7):
            with self.subTest(answer=repr(bad)):

                class BadAnswer:
                    def __init__(self, answer):
                        self.answer = answer
                        self.calls = 0

                    def ask(self, state, questions, retries=None,
                            timeout=None):
                        self.calls += 1
                        return {qid: self.answer for qid in questions}

                client = BadAnswer(bad)
                result = self.check(VIOLATING_REPLY, client)
                self.assertEqual(result["status"], "unchecked",
                                 f"answer {bad!r}: {result}")
                self.assertEqual(result["fired"], [])
                self.assertTrue(result["reason"].strip(),
                                "an unchecked result carries a plain reason")
                self.assertEqual(client.calls, 1)


class TestAGuttedChecksFileIsAnnounced(ReplyRuleCheckTestCase):
    """AC1: a checks file that is valid JSON but neutered -- no checks, an
    impossible threshold, a check with no question -- is announced as
    unchecked, never passed silently as clean. The classifier is never
    consulted, because there is nothing valid to ask it."""

    def _write_checks(self, checks):
        path = Path(self.tmp) / "gutted_checks.json"
        path.write_text(json.dumps({"checks": checks}), encoding="utf-8")
        return path

    def test_empty_or_impossible_checks_are_announced(self):
        good = {"rule": self.check_spec["rule"],
                "question": self.check_spec["question"],
                "threshold": self.check_spec["threshold"]}
        cases = {
            "no checks": [],
            "threshold above 1": [{**good, "threshold": 9.9}],
            "threshold 0": [{**good, "threshold": 0}],
            "empty question": [{**good, "question": ""}],
        }
        for label, checks in cases.items():
            with self.subTest(case=label):
                client = FakeClient(0.99)
                result = reply_rule_check.check(
                    VIOLATING_REPLY, memory_dir=self.memory_dir,
                    client=client, checks_path=self._write_checks(checks))
                self.assertEqual(result["status"], "unchecked",
                                 f"{label}: {result}")
                self.assertEqual(result["fired"], [])
                self.assertTrue(result["reason"].strip(),
                                "an unchecked result carries a plain reason")
                self.assertEqual(len(client.calls), 0,
                                 "the client must never be consulted")


class TestWhatIsSentIsBoundedAndScrubbed(ReplyRuleCheckTestCase):
    """AC3: what leaves the machine is at most the reply's last 4000
    characters, scrubbed of home paths, bearer tokens, password values,
    emails and key-shaped strings -- before the cut is taken."""

    def test_length_and_secrets_are_removed_before_sending(self):
        # Built by concatenation so the test file itself contains no
        # machine-local home-path literal (AC5 checks this file too).
        home_prefix = HOME_LITERAL
        secret_tail = (
            "config lives at " + home_prefix + "patrick/deploy.conf "
            "auth Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC1example "
            "password=S3cretPassValueHere "
            "contact ops@example.net "
            "handle abcdefghij1234567890KQz9 end"
        )
        reply = ("word " * 1000).strip() + "\n\n" + secret_tail  # > 4000
        client = FakeClient(0.5)
        self.check(reply, client)

        self.assertEqual(len(client.calls), 1)
        state = client.calls[0]["state"]
        self.assertIsInstance(state, str)
        self.assertLessEqual(len(state), 4000)
        # Every scrub rule has fired:
        self.assertNotIn(home_prefix, state)
        self.assertIn("~", state)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVC1example", state)
        self.assertIn("Bearer [redacted]", state)
        self.assertNotIn("S3cretPassValueHere", state)
        self.assertIn("password=[redacted]", state)
        self.assertNotIn("ops@example.net", state)
        self.assertIn("[email]", state)
        self.assertNotIn("abcdefghij1234567890KQz9", state)
        self.assertIn("[redacted]", state)

    def test_account_key_values_are_scrubbed_whole(self):
        # CSO round-3 finding B: a separator-bearing AccountKey= base64
        # leaked most of its characters; the scrub must take the WHOLE
        # value for any name containing key/secret/token/password, in
        # name=value or name: value form, compound names included.
        secrets = {
            "AccountKey": "JX7Zk/R9mQvP+2wL5nE8yT3aHf6/dS1gU4bC0oKiMq7+==",
            "SharedAccessKey": "sr=A&sig=abcdEFGH1234ijklMNOP5678qrstUVWX",
            "x-api-token": "sk-live-abcdef123456",
        }
        reply = ("connection follows.\n\n"
                 f"AccountKey={secrets['AccountKey']};Endpoint=core\n"
                 f"SharedAccessKey={secrets['SharedAccessKey']}\n"
                 f"x-api-token: {secrets['x-api-token']}\n"
                 "end of config")
        client = FakeClient(0.5)
        self.check(reply, client)

        state = client.calls[0]["state"]
        for name, value in secrets.items():
            with self.subTest(name=name):
                # No character run of the secret value survives...
                self.assertNotIn(value, state)
                for i in range(0, len(value) - 3):
                    self.assertNotIn(value[i:i + 4], state,
                                     f"fragment {value[i:i + 4]!r} of "
                                     f"{name} reached the classifier")
                # ...and the name is still there, value replaced whole.
                self.assertIn(name, state)
        self.assertEqual(state.count("[redacted]"), 3)


class TestAHungServiceIsBounded(ReplyRuleCheckTestCase):
    """AC4: a hung classifier holds a reply for no more than about 15
    seconds -- one short attempt."""

    def test_one_short_attempt(self):
        client = FakeClient(0.5)
        self.check(CLEAN_REPLY, client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["retries"], 1)
        self.assertEqual(client.calls[0]["timeout"], 10)


class TestNothingPersonalIsCommitted(unittest.TestCase):
    """AC5: nothing personal or machine-local is committed -- no home path
    in the helper, hook, data file or test file, no session key in the data
    file, and no quotation from Patrick in the memory fixture."""

    def test_no_home_path_session_ids_or_memory_text(self):
        files = [
            HELPERS / "reply_rule_check.py",
            REPO / ".claude" / "hooks" / "reply_rule_guard.py",
            HELPERS / "data" / "reply_rule_checks.json",
            Path(__file__),
        ]
        for f in files:
            with self.subTest(file=f.name):
                self.assertNotIn(HOME_LITERAL, f.read_text(encoding="utf-8"))

        data = json.loads(
            (HELPERS / "data" / "reply_rule_checks.json").read_text(
                encoding="utf-8"))

        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from keys(v)
            elif isinstance(node, list):
                for v in node:
                    yield from keys(v)

        self.assertNotIn("session", list(keys(data)),
                         "no session identifier key in the data file")

        # The memory fixture has the live note's shape (description line +
        # "How to apply:" list) and quotes nothing Patrick said.
        self.assertIn("description:", ASK_ON_THE_BOARD_MEMORY)
        self.assertIn("**How to apply:**", ASK_ON_THE_BOARD_MEMORY)
        self.assertNotIn("Patrick", ASK_ON_THE_BOARD_MEMORY)


if __name__ == "__main__":
    unittest.main()
