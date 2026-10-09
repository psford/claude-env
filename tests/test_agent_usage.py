#!/usr/bin/env python3
"""scripts/agent_usage.py (2026-10-08): per-subagent model, tokens and cost
from a session's logs. Pins the de-duplication (one API response spans
several log lines), the --since filter and the list-price arithmetic.

Run directly: python3 tests/test_agent_usage.py
"""
import importlib.util
import json
import os
import tempfile
import unittest

_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "agent_usage.py")
_spec = importlib.util.spec_from_file_location("agent_usage", _path)
au = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(au)


def line(msg_id, model, stamp, out, read=1000, write=0, text=""):
    return json.dumps({"type": "assistant", "timestamp": stamp, "message": {
        "id": msg_id, "model": model, "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 2, "output_tokens": out, "cache_read_input_tokens": read,
                  "cache_creation_input_tokens": write,
                  "cache_creation": {"ephemeral_5m_input_tokens": write, "ephemeral_1h_input_tokens": 0}}}})


class AgentUsageTest(unittest.TestCase):
    def setUp(self):
        self.session = tempfile.mkdtemp()
        sub = os.path.join(self.session, "subagents")
        os.makedirs(os.path.join(sub, "workflows", "wf_1"))
        with open(os.path.join(sub, "agent-a.jsonl"), "w") as h:
            # one response written as three lines: count once, largest usage
            h.write(line("m1", "claude-opus-5-5", "2026-10-08T01:00:00Z", 10, write=1_000_000) + "\n")
            h.write(line("m1", "claude-opus-5-5", "2026-10-08T01:00:01Z", 500_000, write=1_000_000) + "\n")
            h.write(line("m1", "claude-opus-5-5", "2026-10-08T01:00:02Z", 20, write=1_000_000, text="x" * 400) + "\n")
        with open(os.path.join(sub, "agent-a.meta.json"), "w") as h:
            json.dump({"description": "review thing", "model": "opus"}, h)
        with open(os.path.join(sub, "workflows", "wf_1", "agent-b.jsonl"), "w") as h:
            h.write(line("m2", "claude-haiku-5-5", "2026-10-07T23:00:00Z", 1000, read=2_000_000) + "\n")

    def test_dedupes_and_prices(self):
        rows = {r["model"]: r for r in au.collect(self.session)}
        opus = rows["opus"]
        self.assertEqual(opus["requests"], 1)
        self.assertEqual((opus["w5"], opus["out"], opus["read"]), (1_000_000, 500_000, 1000))
        # 1M write x $5 + 0.5M out x $20 + 1000 read x $0.20/M + 2 in x $4/M
        self.assertAlmostEqual(opus["cost"], 5 + 10 + 0.0002 + 0.000008, places=6)
        self.assertEqual(opus["label"], "review thing")
        self.assertEqual(opus["visible_out_est"], 100)
        self.assertAlmostEqual(rows["haiku"]["cost"], 2 * 0.01 + 1000 * 0.5 / 1e6 + 2 * 0.1 / 1e6, places=9)
        self.assertEqual(rows["haiku"]["workflow"], "wf_1")

    def test_since_filters_by_start(self):
        rows = au.collect(self.session, since="2026-10-08T00:00:00Z")
        self.assertEqual([r["model"] for r in rows], ["opus"])


if __name__ == "__main__":
    unittest.main()
