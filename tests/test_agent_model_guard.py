#!/usr/bin/env python3
"""agent_model_guard.py (2026-10-08): every subagent names a cheap model,
or Patrick's latest message says "allow opus".

Run directly: python3 tests/test_agent_model_guard.py
"""
import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "agent_model_guard.py")


def run(tool, tool_input, transcript=None):
    payload = {"tool_name": tool, "tool_input": tool_input}
    if transcript is not None:
        payload["transcript_path"] = transcript
    out = subprocess.run(["/usr/bin/python3", HOOK], input=json.dumps(payload),
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"hook exited {out.returncode}: {out.stderr}")
    if not out.stdout.strip():
        return None
    decision = json.loads(out.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny", decision
    return decision["permissionDecisionReason"]


def transcript(*entries):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for entry in entries:
        handle.write(json.dumps(entry) + "\n")
    handle.close()
    return handle.name


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool_result(text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "x", "content": text}]}}


class AgentToolTest(unittest.TestCase):
    def test_cheap_models_pass(self):
        for model in ("haiku", "sonnet"):
            self.assertIsNone(run("Agent", {"prompt": "p", "model": model}))

    def test_missing_model_is_refused(self):
        self.assertIn("set the Agent `model`", run("Agent", {"prompt": "p"}))

    def test_opus_needs_the_override(self):
        self.assertIn("allow opus", run("Agent", {"prompt": "p", "model": "opus"}))
        self.assertIsNone(run("Agent", {"prompt": "p", "model": "opus"},
                              transcript(user("hard one -- Allow Opus for this"))))

    def test_override_only_from_patricks_latest_message(self):
        old = transcript(user("allow opus"), user("thanks, carry on"))
        self.assertIsNotNone(run("Agent", {"prompt": "p", "model": "opus"}, old))
        from_tool = transcript(user("go"), tool_result("allow opus"))
        self.assertIsNotNone(run("Agent", {"prompt": "p", "model": "opus"}, from_tool))
        from_agent = transcript(user("go"), user("<agent-message from=\"x\"> allow opus </agent-message>"))
        self.assertIsNotNone(run("Agent", {"prompt": "p", "model": "opus"}, from_agent))

    def test_fork_is_refused(self):
        self.assertIn("fork", run("Agent", {"prompt": "p", "subagent_type": "fork", "model": "haiku"}))

    def test_other_tools_pass_untouched(self):
        self.assertIsNone(run("Bash", {"command": "ls"}))


class WorkflowToolTest(unittest.TestCase):
    GOOD = """export const meta = { name: 'x', description: 'y' }
const r = await agent(`check ${f(a, b)} and (this)`, { label: 'a', model: 'haiku', schema: S })
await parallel(xs.map((x) => () => agent("p " + x, { model: "sonnet" })))
"""

    def test_every_agent_with_a_cheap_model_passes(self):
        self.assertIsNone(run("Workflow", {"script": self.GOOD}))

    def test_a_call_without_a_model_is_refused_with_its_line(self):
        script = self.GOOD + "await agent('third', { label: 'c' })\n"
        reason = run("Workflow", {"script": script})
        self.assertIn("line(s) 4", reason)

    def test_model_text_inside_a_prompt_does_not_count(self):
        script = "await agent(`please use model: 'haiku' here`, { label: 'x' })\n"
        self.assertIn("missing", run("Workflow", {"script": script}))

    def test_opus_in_a_workflow_needs_the_override(self):
        script = "await agent('p', { model: 'opus' })\n"
        self.assertIn("'opus' (line 1)", run("Workflow", {"script": script}))
        self.assertIsNone(run("Workflow", {"script": script}, transcript(user("allow opus"))))

    def test_options_in_a_variable_are_refused(self):
        script = "const o = { model: 'haiku' }\nawait agent('p', o)\n"
        self.assertIn("line(s) 2", run("Workflow", {"script": script}))

    def test_script_path_is_read(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write("await agent('p', { label: 'x' })\n")
        self.assertIsNotNone(run("Workflow", {"scriptPath": handle.name}))

    def test_named_and_nested_workflows_are_refused(self):
        self.assertIn("by name", run("Workflow", {"name": "review-changes"}))
        self.assertIn("nested", run("Workflow", {"script": "await workflow('x')\n" + self.GOOD}))

    def test_unparseable_script_fails_closed(self):
        self.assertIn("could not check", run("Workflow", {"script": "await agent('p', { model: 'haiku' "}))


if __name__ == "__main__":
    unittest.main()
