#!/usr/bin/env python3
"""refusal_ends_the_run: a subagent that has been refused once gets no
further tool calls.

CE-12.14. Drives the real hook as a subprocess with a JSON payload on
stdin, exactly as Claude Code would invoke it, against a synthetic
`<project dir>/<session_id>/subagents/agent-<agent_id>.jsonl` transcript
built fresh per test. The shapes below (an assistant `tool_use` block
correlated by `tool_use_id` to a `user` `tool_result` block) mirror real
subagent transcripts read under
~/.claude/projects/-home-patrick-projects-claude-env/*/subagents/ while
building this hook -- not copied from one, built to match what was
observed there.

A denial shows up in a transcript two ways, and both are covered:
  - the plain exit-2/stderr protocol, which Claude Code wraps as
    "PreToolUse:<Tool> hook error: [<command>]: <text>"; and
  - the JSON permissionDecision "deny" protocol, recorded as the hook's
    permissionDecisionReason text directly (by convention in this repo,
    starting with "BLOCKED").

Run: python3 .claude/hooks/tests/test_refusal_ends_the_run.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "refusal_ends_the_run.py")


def tool_use_line(tool_use_id, name, tool_input):
    return json.dumps({
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input},
            ],
        },
    })


def tool_result_line(tool_use_id, text, is_error=True):
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id,
                 "content": text, "is_error": is_error},
            ],
        },
    })


class RefusalCase(unittest.TestCase):
    def setUp(self):
        self.project_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-r", "--", self.project_dir], check=False))
        self.session_id = "session-1234"
        self.agent_id = "aabbccdd1122"
        self.transcript_path = os.path.join(self.project_dir, f"{self.session_id}.jsonl")
        # transcript_path itself just needs to exist as a file -- it's the
        # PARENT session's transcript, which this hook never reads; only its
        # dirname + session_id are used to locate the subagent's own file.
        with open(self.transcript_path, "w", encoding="utf-8"):
            pass
        self.subagents_dir = os.path.join(self.project_dir, self.session_id, "subagents")

    def write_subagent_transcript(self, lines):
        os.makedirs(self.subagents_dir, exist_ok=True)
        path = os.path.join(self.subagents_dir, f"agent-{self.agent_id}.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def payload(self, tool_name="Write", tool_input=None, agent_id="__default__"):
        p = {
            "tool_name": tool_name,
            "tool_input": tool_input or {"file_path": "/tmp/report.md"},
            "transcript_path": self.transcript_path,
            "session_id": self.session_id,
        }
        p["agent_id"] = self.agent_id if agent_id == "__default__" else agent_id
        if p["agent_id"] is None:
            del p["agent_id"]
        return p

    def run_hook(self, payload):
        done = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=15)
        out = {}
        if done.stdout.strip():
            out = json.loads(done.stdout)
        return done.returncode, (out.get("hookSpecificOutput") or {})


class TestARefusalEndsTheRun(RefusalCase):
    """All three ACs for CE-12.14 as methods of one class, per the ticket's
    named Check commands (TestARefusalEndsTheRun.<method>)."""

    # AC1
    def test_the_call_after_a_refusal_is_denied(self):
        cases = [
            (
                "hook-error protocol",
                ("PreToolUse:Bash hook error: [test -f .../main_branch_guard.py "
                 "|| exit 0; python3 .../main_branch_guard.py]: BLOCKED: cannot "
                 "determine the target branch. Fail-closed: refusing a "
                 "commit/merge whose branch is unknown.\n"),
                {"command": "git commit -m test"},
                "Bash",
            ),
            (
                "permissionDecision-deny protocol",
                ("BLOCKED: an agent session is still running after whatever "
                 "launched it exited.\n\nThese are reparented to init -- "
                 "nothing is supervising them.\n"),
                {"command": "ps aux"},
                "Bash",
            ),
        ]
        for label, refusal_text, refused_input, refused_tool in cases:
            with self.subTest(label=label):
                self.write_subagent_transcript([
                    tool_use_line("toolu_1", refused_tool, refused_input),
                    tool_result_line("toolu_1", refusal_text, is_error=True),
                ])
                rc, spec = self.run_hook(self.payload(
                    tool_name="Write", tool_input={"file_path": "/tmp/next-step.py"}))

                self.assertEqual(rc, 2, f"{label}: expected the next call denied")
                self.assertEqual(spec.get("permissionDecision"), "deny", label)
                reason = spec.get("permissionDecisionReason", "")
                self.assertIn(refused_input["command"], reason,
                             f"{label}: refused command not named in the denial")
                self.assertIn(refusal_text.split("\n", 1)[0].strip(), reason,
                             f"{label}: first line of the refusal not carried over")
                self.assertIn("stop", reason.lower(), label)
                self.assertIn("report", reason.lower(), label)

    # AC2
    def test_an_agent_with_no_earlier_refusal_and_the_main_session_are_untouched(self):
        # A subagent transcript with tool calls that all succeeded.
        self.write_subagent_transcript([
            tool_use_line("toolu_1", "Bash", {"command": "ls"}),
            tool_result_line("toolu_1", "file1.txt\nfile2.txt\n", is_error=False),
        ])
        rc, spec = self.run_hook(self.payload(agent_id=self.agent_id))
        self.assertEqual(rc, 0, "an agent with no earlier refusal must not be denied")
        self.assertEqual(spec, {}, "a clean transcript must produce no output at all")

        # The main session: no agent_id on the payload at all, even though
        # THIS SAME transcript file (keyed by this test's session_id) holds a
        # denial for some agent_id. Absence of agent_id must short-circuit
        # before any transcript is ever consulted.
        self.write_subagent_transcript([
            tool_use_line("toolu_1", "Bash", {"command": "git commit -m x"}),
            tool_result_line("toolu_1", "BLOCKED: refused.\n", is_error=True),
        ])
        payload = self.payload(agent_id=None)
        self.assertNotIn("agent_id", payload)
        rc, spec = self.run_hook(payload)
        self.assertEqual(rc, 0, "the main session must never be denied by this hook")
        self.assertEqual(spec, {}, "the main session call must be completely untouched")

    # AC3
    def test_an_unreadable_transcript_is_named_and_the_call_allowed(self):
        # No subagent transcript was ever written -- self.subagents_dir does
        # not exist, so the file this hook looks for cannot be there.
        missing_path = os.path.join(self.subagents_dir, f"agent-{self.agent_id}.jsonl")
        rc, spec = self.run_hook(self.payload(agent_id=self.agent_id))

        self.assertEqual(rc, 0, "a missing transcript must never gag the agent")
        self.assertEqual(spec.get("permissionDecision"), "allow")
        note = spec.get("additionalContext", "")
        self.assertIn(missing_path, note, "the missing transcript path must be named")

        # Unreadable in a different way: the path exists but is a directory,
        # so opening it for read raises OSError (IsADirectoryError) rather
        # than FileNotFoundError -- the two are different failure shapes and
        # both must fail open.
        os.makedirs(missing_path, exist_ok=True)
        rc2, spec2 = self.run_hook(self.payload(agent_id=self.agent_id))
        self.assertEqual(rc2, 0, "an unreadable transcript must never gag the agent")
        self.assertEqual(spec2.get("permissionDecision"), "allow")
        self.assertIn(missing_path, spec2.get("additionalContext", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
