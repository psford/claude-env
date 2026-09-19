#!/usr/bin/env python3
"""Test agent_refusal_tally.py, the PostToolUse/Agent hook that counts a
finished subagent's refusals from its OWN transcript rather than from its
final report (CE-12.15).

Drives the real hook as a subprocess with a JSON payload on stdin, the way
test_deploy_guard.py and its siblings do. Each test lays out a synthetic
subagent transcript as a temporary .jsonl file, in the exact directory shape
the hook expects: <dir>/<session_id>/subagents/agent-<agent_id>.jsonl,
sibling to the parent session's own <dir>/<session_id>.jsonl (the path the
hook is handed as `transcript_path`).

A denial in a real transcript renders as an is_error tool_result in one of
two shapes (see agent_refusal_tally.py's own docstring for how this was
established by reading real transcripts under
~/.claude/projects/*/subagents/ — none of that data is reproduced here,
only its shape):
  * a bare permissionDecision "deny" with no reason: content is exactly
    "Hook PreToolUse:<Tool> denied this tool";
  * an error tool_result carrying the guard's own refusal text, prefixed
    "PreToolUse:<Tool> hook error: [<cmd>]: <text>", where <text> in this
    repo's guards always starts "BLOCKED: ...".
Both shapes are exercised below.

Run: python3 .claude/hooks/tests/test_agent_refusal_tally.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HOOK = os.path.join(HOOKS, "agent_refusal_tally.py")


def _write_subagent_transcript(root, session_id, agent_id, records):
    """Lay out <root>/<session_id>/subagents/agent-<agent_id>.jsonl the way
    Claude Code does, and return the parent session's own transcript_path
    (<root>/<session_id>.jsonl) — the hook derives the subagents directory
    from that path's dirname plus session_id, so the file itself need not
    exist."""
    subagents_dir = os.path.join(root, session_id, "subagents")
    os.makedirs(subagents_dir, exist_ok=True)
    path = os.path.join(subagents_dir, f"agent-{agent_id}.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
    return os.path.join(root, f"{session_id}.jsonl")


def _run_hook(payload):
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True, text=True, check=False,
    )


def _additional_context(proc):
    if not proc.stdout.strip():
        return None
    out = json.loads(proc.stdout)
    return out.get("hookSpecificOutput", {}).get("additionalContext")


def _tool_use(tool_use_id, name, tool_input):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tool_use_id, "name": name, "input": tool_input}
    ]}}


def _tool_result(tool_use_id, content, is_error):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use_id, "is_error": is_error,
         "content": content}
    ]}}


class TestEveryRefusalIsCounted(unittest.TestCase):
    """CE-12.15 AC1/AC2: a finished subagent's transcript, not its report, is
    what gets counted."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_refusal_in_the_transcript_is_printed_with_its_command(self):
        """AC1: several denials, both shapes, each printed with its tool,
        the first line of its refusal, and the start of the command/path
        that caused it. At HEAD nothing reads a finished agent's transcript
        at all, so this is a new capability, not a regression check."""
        session_id = "sess-many-denials"
        agent_id = "aaaa1111bbbb2222c"

        bash_refusal = (
            'PreToolUse:Bash hook error: [python3 "/plugins/psford-tickets/hooks/'
            'ticket_commit_guard.py"]: BLOCKED: this commit names no ticket.\n\n'
            'On a feature branch in a repo with a ticket store, name the ticket.'
        )
        agent_refusal = (
            'PreToolUse:Agent hook error: [python3 "/plugins/psford-tickets/hooks/'
            'enforce_subagent_model.py"]: BLOCKED: subagent model must be sonnet '
            'or haiku (got: unset).'
        )
        records = [
            _tool_use("toolu_bash1", "Bash",
                      {"command": 'git commit -m "fix: something without a ticket"'}),
            _tool_result("toolu_bash1", bash_refusal, True),
            _tool_use("toolu_write1", "Write",
                      {"file_path": "/home/patrick/projects/claude-env/protected/config.py"}),
            _tool_result("toolu_write1", "Hook PreToolUse:Write denied this tool", True),
            _tool_use("toolu_agent1", "Agent",
                      {"description": "dispatch x", "subagent_type": "general-purpose",
                       "prompt": "do the thing"}),
            _tool_result("toolu_agent1", agent_refusal, True),
        ]
        transcript_path = _write_subagent_transcript(self.tmp, session_id, agent_id, records)

        proc = _run_hook({
            "session_id": session_id,
            "transcript_path": transcript_path,
            "tool_response": {"status": "completed", "agentId": agent_id},
        })

        self.assertEqual(proc.returncode, 0, f"hook must always exit 0; stderr={proc.stderr!r}")
        context = _additional_context(proc)
        self.assertIsNotNone(context, f"expected additionalContext, got stdout={proc.stdout!r}")

        self.assertIn("3 refusal(s)", context)

        # Denial 1: Bash, "hook error" shape -- tool, first line, command.
        self.assertIn("Bash", context)
        self.assertIn(
            'PreToolUse:Bash hook error: [python3 "/plugins/psford-tickets/hooks/'
            'ticket_commit_guard.py"]: BLOCKED: this commit names no ticket.',
            context,
        )
        self.assertNotIn("name the ticket", context)  # second line of the refusal, not printed
        self.assertIn('git commit -m "fix: something without a ticket"', context)

        # Denial 2: Write, bare permissionDecision-deny shape -- tool, text, path.
        self.assertIn("Write", context)
        self.assertIn("Hook PreToolUse:Write denied this tool", context)
        self.assertIn("/home/patrick/projects/claude-env/protected/config.py", context)

        # Denial 3: Agent, "hook error" shape -- tool, first line, command.
        self.assertIn("Agent", context)
        self.assertIn(
            'PreToolUse:Agent hook error: [python3 "/plugins/psford-tickets/hooks/'
            'enforce_subagent_model.py"]: BLOCKED: subagent model must be sonnet '
            'or haiku (got: unset).',
            context,
        )

    def test_no_refusals_says_so_and_an_unreadable_transcript_says_that(self):
        """AC2: zero denials says so in words, and a missing/unreadable
        transcript says exactly that -- the two must never look alike, and
        neither ever prints a bare "0 refusal(s)"."""
        session_id = "sess-clean-run"
        agent_id = "cccc3333dddd4444e"
        records = [
            _tool_use("toolu_ls1", "Bash", {"command": "ls -la"}),
            _tool_result("toolu_ls1", "total 0\n", False),
        ]
        transcript_path = _write_subagent_transcript(self.tmp, session_id, agent_id, records)

        # (a) transcript exists and is readable, but holds no denial.
        clean_proc = _run_hook({
            "session_id": session_id,
            "transcript_path": transcript_path,
            "tool_response": {"status": "completed", "agentId": agent_id},
        })
        self.assertEqual(clean_proc.returncode, 0, clean_proc.stderr)
        clean_context = _additional_context(clean_proc)
        self.assertIsNotNone(clean_context, f"expected additionalContext, got stdout={clean_proc.stdout!r}")
        self.assertIn("no refusals were found", clean_context.lower())
        self.assertNotIn("0 refusal", clean_context)

        # (b) transcript missing entirely -- an agent_id with no .jsonl on disk.
        missing_proc = _run_hook({
            "session_id": session_id,
            "transcript_path": transcript_path,
            "tool_response": {"status": "completed", "agentId": "no-such-agent-id"},
        })
        self.assertEqual(missing_proc.returncode, 0, missing_proc.stderr)
        missing_context = _additional_context(missing_proc)
        self.assertIsNotNone(missing_context, f"expected additionalContext, got stdout={missing_proc.stdout!r}")
        self.assertIn("could not be read", missing_context)
        self.assertNotIn("0 refusal", missing_context)
        self.assertNotIn("no refusals were found", missing_context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
