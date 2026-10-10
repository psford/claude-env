#!/usr/bin/env python3
"""todo-sync normalized matching + todo-relay notice draining (2026-10-10).

The #240/#241 incident: a session todo_create'd a tracked title with one
trailing period; exact-match dedupe missed it and a duplicate issue was
filed, and the session saw no feedback at all (post_tool_use output is
discarded). These tests pin the fixes: normalized title matching, and the
session-tagged notice file that todo-relay.sh drains into the session.

Run directly: python3 tests/test_todo_sync_relay.py
"""
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_HOOK = os.path.join(REPO, "polytoken", "hooks", "todo-sync.sh")
RELAY_HOOK = os.path.join(REPO, "polytoken", "hooks", "todo-relay.sh")

TRACKED_TITLE = "Handoff test: Mac session adopts and completes this tracked todo"
LIST_JSON = json.dumps([
    {"number": 240, "title": TRACKED_TITLE, "body": "session:old\nmachine:vm",
     "labels": [{"name": "todo"}]},
])


class TodoSyncHarness(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.mkdtemp(prefix="todo-sync-test.")
        self.addCleanup(shutil.rmtree, self.state, True)
        # Session pointer, as todo-restore.sh would write it.
        with open(os.path.join(self.state, "todo-session.current"), "w") as f:
            f.write("testsess 0\n")
        self.gh_calls = os.path.join(self.state, "gh-calls.log")
        self.gh = os.path.join(self.state, "gh-stub")
        stub = (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> " + shlex.quote(self.gh_calls) + "\n"
            "case \"$1 $2\" in\n"
            "  'issue create') echo https://github.com/psford/claude-env/issues/999 ;;\n"
            "  'issue list') printf '%s' " + shlex.quote(LIST_JSON) + " ;;\n"
            "esac\n"
        )
        with open(self.gh, "w") as f:
            f.write(stub)
        os.chmod(self.gh, 0o755)

    def env(self):
        env = dict(os.environ)
        env.update(POLYTOKEN_STATE_HOME=self.state,
                   POLYTOKEN_SESSION_ID="testsess",
                   GH_BIN=self.gh)
        return env

    def run_sync(self, tool, tool_input):
        event = json.dumps({"event": "post_tool_use", "tool_name": tool,
                            "input": tool_input})
        return subprocess.run(["bash", SYNC_HOOK], input=event.encode(),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.env())

    def run_relay(self, event=None):
        event = event or {"event": "pre_model_turn"}
        return subprocess.run(["bash", RELAY_HOOK],
                              input=json.dumps(event).encode(),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.env())

    def gh_called_create(self):
        try:
            with open(self.gh_calls) as f:
                return any(line.startswith("issue create ") for line in f)
        except FileNotFoundError:
            return False

    def notices(self):
        try:
            with open(os.path.join(self.state, "todo-notices.pending")) as f:
                return f.read()
        except FileNotFoundError:
            return ""


class TestNormalizedMatching(TodoSyncHarness):
    def test_trailing_period_dedupes_instead_of_filing(self):
        """The #241 regression: same title + '.' must adopt, not file."""
        self.run_sync("todo_create",
                      {"title": TRACKED_TITLE + ".",
                       "description": "adopted copy"})
        self.assertFalse(self.gh_called_create(),
                         "dedupe failed: gh issue create was called")
        self.assertIn("dedupe: issue #240", self.notices())

    def test_whitespace_only_difference_dedupes(self):
        self.run_sync("todo_create",
                      {"title": "  Handoff  test: Mac session adopts and "
                                "completes this tracked  todo "})
        self.assertFalse(self.gh_called_create())
        self.assertIn("dedupe: issue #240", self.notices())

    def test_genuinely_new_title_files_issue(self):
        self.run_sync("todo_create",
                      {"title": "A genuinely different todo",
                       "description": "d"})
        self.assertTrue(self.gh_called_create())
        self.assertIn("created issue 999", self.notices())


class TestRelayDraining(TodoSyncHarness):
    def notices_file(self):
        return os.path.join(self.state, "todo-notices.pending")

    def test_drains_own_and_unknown_leaves_foreign(self):
        with open(self.notices_file(), "w") as f:
            f.write("session:testsess\ttodo_create: dedupe: issue #240 "
                    "already tracks 'X'\n"
                    "session:other\ttodo_create: created issue 999 for 'Y'\n"
                    "session:?\ttodo_create: gh not found — cannot sync\n")
        r = self.run_relay()
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.decode())
        self.assertEqual(out["outcome"], "proceed")
        ctx = out["additional_context"]
        self.assertIn("#240", ctx)
        self.assertIn("gh not found", ctx)
        self.assertNotIn("999", ctx)
        with open(self.notices_file()) as f:
            left = f.read()
        self.assertIn("session:other", left)
        self.assertNotIn("session:testsess", left)
        self.assertNotIn("session:?", left)

    def test_second_run_is_silent_for_this_session(self):
        with open(self.notices_file(), "w") as f:
            f.write("session:other\ttodo_create: created issue 999 for 'Y'\n")
        r = self.run_relay()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, b"")

    def test_no_notices_file_is_silent_fast_path(self):
        r = self.run_relay()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, b"")


if __name__ == "__main__":
    unittest.main()
