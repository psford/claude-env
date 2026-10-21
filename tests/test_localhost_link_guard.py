#!/usr/bin/env python3
"""localhost_link_guard: no localhost link reaches Patrick unless docs/ports.md was read first.

Patrick, 2026-10-20: "I want the hook to smash the agent any time it tries to
pass me a link to localhost without first checking the registry." That day's
reply -- "open http://localhost:5143/admin", with no read of the registry --
is the first case below.

Each test writes a session transcript the way Claude Code stores it (one JSON
entry per line: Patrick's message, then the agent's tool calls, tool results
and text), feeds the hook a Stop payload through subprocess, and reads its
decision. The ports are real registry entries: 5143 and 10000 are road-trip's;
59999 is in no row.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "localhost_link_guard.py")
REGISTRY = os.path.join(ROOT, "docs", "ports.md")


def patrick(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def says(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


_ids = iter(range(1, 10_000))


def calls(name, **args):
    """A tool call and its result, as two transcript entries."""
    tid = f"toolu_{next(_ids)}"
    return [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": args}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tid, "content": "ok"}]}},
    ]


READ_REGISTRY = calls("Read", file_path=REGISTRY)


def flatten(*parts):
    out = []
    for p in parts:
        out.extend(p if isinstance(p, list) else [p])
    return out


class LocalhostLinkGuard(unittest.TestCase):
    def run_hook(self, entries, stop_hook_active=False, raw_stdin=None, transcript_path=None, last_assistant_message=None):
        if transcript_path is None:
            fd, transcript_path = tempfile.mkstemp(suffix=".jsonl")
            self.addCleanup(os.remove, transcript_path)
            with os.fdopen(fd, "w") as fh:
                for e in entries:
                    fh.write(json.dumps(e) + "\n")
        payload = {"transcript_path": transcript_path, "stop_hook_active": stop_hook_active, "hook_event_name": "Stop"}
        if last_assistant_message is not None:
            payload["last_assistant_message"] = last_assistant_message
        stdin = raw_stdin if raw_stdin is not None else json.dumps(payload)
        result = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def assertBlocked(self, decision, *phrases):
        self.assertIsNotNone(decision, "expected a block")
        self.assertEqual(decision["decision"], "block")
        for phrase in phrases:
            self.assertIn(phrase, decision["reason"])

    # -- 2026-10-20 -------------------------------------------------------

    def test_the_reply_from_2026_10_20_is_blocked(self):
        decision = self.run_hook(flatten(
            patrick("we have a registration for ports used by different projects"),
            says("The local site is ready: open http://localhost:5143/admin and sign in.")))
        self.assertBlocked(decision, "localhost:5143", "without reading the port registry", "docs/ports.md")

    def test_reading_the_registry_first_lets_the_link_through(self):
        self.assertIsNone(self.run_hook(flatten(
            patrick("open the review page"), READ_REGISTRY,
            says("It's at http://localhost:5143/admin."))))

    def test_a_bash_or_grep_read_of_the_registry_counts(self):
        for read in (calls("Bash", command=f"cat {REGISTRY}"), calls("Grep", pattern="5143", path=REGISTRY)):
            with self.subTest(tool=read[0]["message"]["content"][0]["name"]):
                self.assertIsNone(self.run_hook(flatten(
                    patrick("where is it?"), read, says("http://localhost:5143/admin"))))

    def test_more_ways_of_reading_the_registry_count(self):
        for command in (f"sed -n 1,30p {REGISTRY}", "python3 helpers/port_lint.py docs/ports.md",
                        f"cd /tmp && grep -n 5143 {REGISTRY}", f"grep -A 3 -e 5143 {REGISTRY}",
                        f"cat {REGISTRY} | head -20"):
            with self.subTest(command=command):
                self.assertIsNone(self.run_hook(flatten(
                    patrick("where?"), calls("Bash", command=command), says("http://localhost:5143/admin"))))

    def test_merely_naming_the_registry_is_not_reading_it(self):
        # 2026-10-20: the commit that added this hook named docs/ports.md in its
        # message, which the first version counted as a read.
        for command in ("git commit -q -F - <<'EOF'\nreads docs/ports.md first\nEOF",
                        'git commit -m "check docs/ports.md"',
                        'gh pr create --body "docs/ports.md is the registry"',
                        "echo docs/ports.md",
                        "cat > notes.txt <<'EOF'\nsee docs/ports.md\nEOF",
                        # the one that let a reply through on 2026-10-20:
                        'python3 -c "c = \'grep -n 5143 docs/ports.md && echo ports.md\'; print(c)"',
                        "grep -rn ports.md .",
                        "sed -n 's/ports.md/registry/p' notes.txt"):
            with self.subTest(command=command):
                self.assertBlocked(self.run_hook(flatten(
                    patrick("where?"), calls("Bash", command=command), says("http://localhost:5143/admin"))),
                    "without reading")

    def test_127_0_0_1_and_ipv6_loopback_are_links_too(self):
        for link in ("http://127.0.0.1:10000/devstoreaccount1", "http://[::1]:5143/"):
            with self.subTest(link=link):
                self.assertBlocked(self.run_hook(flatten(patrick("hi"), says(f"Try {link}"))), "without reading")

    # -- the final reply, which the transcript may not hold yet ------------
    # Hooks reference, Stop input: "the transcript file isn't guaranteed to include
    # the final message at Stop time on all versions" -- use last_assistant_message.

    def test_a_final_reply_missing_from_the_transcript_is_still_judged(self):
        self.assertBlocked(self.run_hook(flatten(patrick("open it"), calls("Bash", command="ls")),
                                         last_assistant_message="Open http://localhost:5143/admin."),
                           "localhost:5143")

    def test_a_final_reply_after_a_registry_read_in_the_transcript_passes(self):
        self.assertIsNone(self.run_hook(flatten(patrick("open it"), READ_REGISTRY),
                                        last_assistant_message="Open http://localhost:5143/admin."))

    def test_a_final_reply_already_in_the_transcript_is_judged_the_same(self):
        reply = "Open http://localhost:5143/admin."
        self.assertBlocked(self.run_hook(flatten(patrick("open it"), says(reply)), last_assistant_message=reply), "localhost:5143")
        self.assertIsNone(self.run_hook(flatten(patrick("open it"), READ_REGISTRY, says(reply)), last_assistant_message=reply))

    # -- ordering and turns -----------------------------------------------

    def test_a_read_after_the_link_is_too_late(self):
        decision = self.run_hook(flatten(
            patrick("open it"), says("Open http://localhost:5143/admin."), READ_REGISTRY, says("Done.")))
        self.assertBlocked(decision, "localhost:5143")

    def test_a_read_in_an_earlier_turn_does_not_count(self):
        decision = self.run_hook(flatten(
            patrick("check the registry"), READ_REGISTRY, says("5143 is road-trip's."),
            patrick("now give me the link"), says("http://localhost:5143/admin")))
        self.assertBlocked(decision, "localhost:5143")

    def test_text_without_a_localhost_port_needs_no_read(self):
        self.assertIsNone(self.run_hook(flatten(
            patrick("status?"), says("CI passed on https://github.com/psford/road-trip/pull/225; localhost isn't involved."))))

    # -- the registry itself ----------------------------------------------

    def test_a_port_the_registry_does_not_list_is_blocked_even_after_reading_it(self):
        decision = self.run_hook(flatten(
            patrick("start it"), READ_REGISTRY, says("Running on http://localhost:59999/.")))
        self.assertBlocked(decision, "localhost:59999", "isn't in the port registry")

    def test_registered_ports_in_a_range_pass(self):
        self.assertIsNone(self.run_hook(flatten(
            patrick("preview?"), READ_REGISTRY, says("Preview dashboard on http://localhost:8795/."))))

    # -- after a block ------------------------------------------------------

    def test_a_retry_that_reads_the_registry_and_gives_the_link_again_passes(self):
        self.assertIsNone(self.run_hook(flatten(
            patrick("open it"), says("Open http://localhost:5143/admin."),
            READ_REGISTRY, says("Checked docs/ports.md: 5143 is road-trip's. Open http://localhost:5143/admin.")),
            stop_hook_active=True))

    def test_a_retry_without_reading_the_registry_is_still_blocked(self):
        self.assertBlocked(self.run_hook(flatten(
            patrick("open it"), says("Open http://localhost:5143/admin."), says("Really, http://localhost:5143/admin.")),
            stop_hook_active=True), "without reading")

    def test_a_retry_that_gives_an_unregistered_port_is_still_blocked(self):
        self.assertBlocked(self.run_hook(flatten(
            patrick("open it"), says("http://localhost:5143/admin"), READ_REGISTRY, says("Use http://localhost:59999/.")),
            stop_hook_active=True), "localhost:59999")

    # -- fails closed ---------------------------------------------------------

    def test_unreadable_input_or_transcript_blocks(self):
        self.assertBlocked(self.run_hook([], raw_stdin="not json"), "couldn't be read")
        self.assertBlocked(self.run_hook([], transcript_path="/nonexistent/transcript.jsonl"), "couldn't be read")


if __name__ == "__main__":
    unittest.main()
