#!/usr/bin/env python3
"""Tests for helpers/memory_scan.py and helpers/memory_scan_hook.py
(CE-2.69).

Every test injects a fake Jev client -- the seam TypeSafeClient.ask sits
behind -- so nothing here opens a socket or reads a key. The memory notes are
synthetic, with the same shape as the live store.
"""

import io
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HELPERS = Path(__file__).resolve().parent.parent
REPO = HELPERS.parent
sys.path.insert(0, str(HELPERS))
import memory_scan  # noqa: E402

HOOK_PATH = HELPERS / "memory_scan_hook.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("memory_scan_hook", HOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def note(key, desc, body):
    return (f"---\nname: {key}\ndescription: \"{desc}\"\n---\n{body}")


class FakeClient:
    """Stands in for TypeSafeClient. ask() records the request and returns
    the given probability map for the choice question."""

    def __init__(self, probabilities, pick=None):
        self.probabilities = probabilities
        self.pick = pick
        self.calls = []

    def ask(self, state, questions, retries=None, timeout=None):
        self.calls.append(
            {"state": state, "questions": questions,
             "retries": retries, "timeout": timeout})
        probs = dict(self.probabilities)
        pick = self.pick
        if pick is None:
            pick = max(probs, key=lambda k: probs[k]) if probs else "none"
        return {qid: (pick, probs.get(pick, 0.0), probs)
                for qid in questions}


class MemoryScanTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.memory_dir = Path(self.tmp) / "memory"
        self.memory_dir.mkdir()
        self.transcript = str(Path(self.tmp) / "session.jsonl")

    def write(self, key, desc, body):
        (self.memory_dir / f"{key}.md").write_text(
            note(key, desc, body), encoding="utf-8")


class TestMemoryScan(MemoryScanTestCase):

    ## AC1

    def test_each_memory_offers_its_description_and_how_to_apply(self):
        self.write("with_how", "A rule with instructions",
                   "Some prose.\n\n**How to apply:**\n- Step one.\n"
                   "- Step two.\n\nRelated: [other]\n")
        self.write("without_how", "A rule with no instructions",
                   "Just prose, nothing structured.\nSecond line.\n")
        self.write("long_how", "A rule with a long section",
                   "**How to apply:**\n- " + "x" * 900 + "\n")

        how = memory_scan.how_to_apply(
            note("k", "d", "p\n\n**How to apply:**\n- Do it.\n"
                 "\nRelated: [x]\n").split("---", 2)[-1])
        self.assertIn("Do it.", how)
        self.assertNotIn("Related:", how)

        how2 = memory_scan.how_to_apply("Plain body only.\nMore.\n")
        self.assertEqual(how2[:17], "Plain body only.\n")
        self.assertLessEqual(len(how2), 600)

        how3 = memory_scan.how_to_apply("y" * 900)
        self.assertEqual(len(how3), 600)

        # The section stops before a following ** heading too.
        how4 = memory_scan.how_to_apply(
            "**How to apply:**\n- Do it.\n\n**See also:**\n- other\n")
        self.assertIn("Do it.", how4)
        self.assertNotIn("See also", how4)
        self.assertNotIn("other", how4.replace("Do it.", ""))

    ## AC2

    def test_one_request_offers_every_memory_and_scrubs_the_action(self):
        long_desc = "D" * 200
        self.write("a", "Alpha rule", "**How to apply:**\n- Alpha step.\n")
        self.write("b", long_desc, "**How to apply:**\n- Beta step.\n")
        self.write("c", "Gamma rule", "no section\n")
        self.write("d", "Delta rule", "**How to apply:**\n- Delta step.\n")

        action = ("Bash: run /home/patrick/secret/path with "
                  "Authorization: Bearer abc123def456 now")
        client = FakeClient({"a": 0.5, "b": 0.2, "c": 0.1, "d": 0.05,
                             "none": 0.15})
        result = memory_scan.scan(action, memory_dir=self.memory_dir,
                                  client=client)

        self.assertEqual(result["status"], "fired")
        self.assertEqual(len(client.calls), 1, "exactly one request")
        call = client.calls[0]
        self.assertIn("action", call["state"])
        self.assertNotIn("/home/patrick", json.dumps(call["state"]))
        self.assertNotIn("secret/path", str(call["state"]))
        self.assertNotIn("abc123def456", str(call["state"]))

        q = call["questions"]["c0"] if "c0" in call["questions"] \
            else list(call["questions"].values())[0]
        self.assertEqual(q["type"], "choice")
        criteria = q["criteria"]
        self.assertIsInstance(criteria, dict)
        self.assertEqual(set(criteria),
                         {"a", "b", "c", "d", "none"})
        self.assertEqual(criteria["a"], "Alpha rule")
        self.assertEqual(len(criteria["b"]), 150)
        self.assertEqual(criteria["b"], "D" * 150)
        self.assertIn("ordinary", criteria["none"].lower())
        self.assertEqual(call["retries"], 1)
        self.assertEqual(call["timeout"], 12)

    ## AC3

    def test_the_top_rules_are_surfaced_and_a_confident_none_is_silent(self):
        for k in "abcd":
            self.write(k, f"Rule {k}", f"**How to apply:**\n- {k} step.\n")

        client = FakeClient({"a": 0.40, "b": 0.25, "c": 0.12, "d": 0.08,
                             "none": 0.15})
        result = memory_scan.scan("git merge --no-ff dev/X-1",
                                  memory_dir=self.memory_dir, client=client)
        self.assertEqual(result["status"], "fired")
        rules = result["rules"]
        self.assertEqual([r["key"] for r in rules], ["a", "b", "c"])
        for r in rules:
            self.assertIn(f"{r['key']} step.", r["how_to_apply"])

        # none at 0.60 or more: nothing is surfaced.
        client = FakeClient({"a": 0.30, "b": 0.05, "none": 0.62})
        result = memory_scan.scan("ls -la", memory_dir=self.memory_dir,
                                  client=client)
        self.assertEqual(result["rules"], [])
        self.assertEqual(result["status"], "clean")

        # Never more than three, and below 0.10 is not surfaced.
        client = FakeClient({"a": 0.5, "b": 0.4, "c": 0.3, "d": 0.2,
                             "none": 0.0})
        result = memory_scan.scan("x", memory_dir=self.memory_dir,
                                  client=client)
        self.assertEqual(len(result["rules"]), 3)
        client = FakeClient({"a": 0.09, "none": 0.2})
        result = memory_scan.scan("x", memory_dir=self.memory_dir,
                                  client=client)
        self.assertEqual(result["rules"], [])

    ## AC5, scan level

    def test_a_scan_that_cannot_run_says_so_and_blocks_nothing(self):
        self.write("a", "Alpha rule", "**How to apply:**\n- Alpha step.\n")

        raising = FakeClient({})
        def blow(state, questions, retries=None, timeout=None):
            raising.calls.append({"state": state})
            raise RuntimeError("network is down")
        raising.ask = blow
        result = memory_scan.scan("x", memory_dir=self.memory_dir,
                                  client=raising)
        self.assertEqual(result["status"], "unchecked")
        self.assertIn("network is down", result["reason"])

        orig = memory_scan.load_api_key
        def no_key(env_file):
            raise RuntimeError("TYPESAFE_API_KEY not found")
        memory_scan.load_api_key = no_key
        try:
            result = memory_scan.scan("x", memory_dir=self.memory_dir,
                                      client=None)
        finally:
            memory_scan.load_api_key = orig
        self.assertEqual(result["status"], "unchecked")
        self.assertIn("key", result["reason"].lower())

    def test_too_many_memories_is_unchecked(self):
        for i in range(255):
            self.write(f"m{i:03d}", "d", "b")
        client = FakeClient({})
        result = memory_scan.scan("x", memory_dir=self.memory_dir,
                                  client=client)
        self.assertEqual(result["status"], "unchecked")
        self.assertIn("254", result["reason"])


class HookTestCase(MemoryScanTestCase):
    def load(self):
        return load_hook()

    def run_main(self, hook, payload, scan):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = hook.main(payload, scan=scan)
        return code, out.getvalue(), err.getvalue()


class FakeScan:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, action_text, memory_dir=None, client=None):
        self.calls.append({"action": action_text, "memory_dir": memory_dir})
        return self.result


class TestTheHookScansConsequentialActionsOnly(HookTestCase):

    FIRED = {"status": "fired",
             "rules": [{"key": "a", "p": 0.42,
                        "how_to_apply": "- Alpha step."}]}

    def test_scans_consequential_bash_and_agent(self):
        hook = self.load()
        payloads = [
            {"tool_name": "Bash",
             "tool_input": {"command": "ticket move X-1 --to uat --url u"}},
            {"tool_name": "Bash",
             "tool_input": {"command": "git merge --no-ff dev/X-1"}},
            {"tool_name": "Bash",
             "tool_input": {"command":
                            "glm-agent dev sonnet --ticket X-1 'go'"}},
            {"tool_name": "Agent",
             "tool_input": {"prompt": "implement the story",
                            "description": "dev dispatch"}},
        ]
        for base in payloads:
            scan = FakeScan(dict(self.FIRED))
            payload = dict(base, transcript_path=self.transcript)
            code, out, err = self.run_main(hook, payload, scan)
            self.assertEqual(code, 0, (payload, err))
            self.assertEqual(len(scan.calls), 1, payload)
            obj = json.loads(out)
            hso = obj["hookSpecificOutput"]
            self.assertEqual(hso["hookEventName"], "PreToolUse")
            ctx = hso["additionalContext"]
            self.assertTrue(ctx.startswith(
                "Jev scanned your saved memories for this action. "
                "Re-read before you proceed:"), ctx)
            self.assertIn("a", ctx)
            self.assertIn("Alpha step.", ctx)
            self.assertIn("0.42", ctx)

    def test_ordinary_commands_are_not_scanned(self):
        hook = self.load()
        for cmd in ("ls -la", "git log --oneline -3"):
            scan = FakeScan(dict(self.FIRED))
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd},
                       "transcript_path": self.transcript}
            code, out, err = self.run_main(hook, payload, scan)
            self.assertEqual(code, 0, err)
            self.assertEqual(scan.calls, [], cmd)
            self.assertEqual(out, "", cmd)


class TestUncheckedHook(HookTestCase):
    def test_unchecked_says_so_and_blocks_nothing(self):
        hook = self.load()
        scan = FakeScan({"status": "unchecked", "rules": [],
                         "reason": "no classifier key"})
        payload = {"tool_name": "Bash",
                   "tool_input": {"command": "ticket move X-1 --to uat"},
                   "transcript_path": self.transcript}
        code, out, err = self.run_main(hook, payload, scan)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("memory scan NOT run:"), err)
        self.assertIn("no classifier key", err)
        self.assertNotIn("deny", out)
        self.assertEqual(json.loads(out) if out.strip() else {}, {})


if __name__ == "__main__":
    unittest.main()
