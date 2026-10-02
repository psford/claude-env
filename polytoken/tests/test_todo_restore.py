"""Unit tests for polytoken/hooks/todo-restore.sh (fake gh via GH_BIN)."""

import json
import os
import time
import unittest

from helpers import sandbox_factory


def start_event(session_id="sess-start"):
    return {"event": "session_start", "matcher_subject": "session_start",
            "session_id": session_id}


def seed_issues(sb, count, wip_number=None, title_fmt="Tracked item %02d"):
    rows = []
    for i in range(1, count + 1):
        labels = [{"name": "todo"}] + ([{"name": "in-progress"}] if i == wip_number else [])
        rows.append({"number": i, "title": title_fmt % i, "state": "open",
                     "labels": labels})
    with open(sb.issues_path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class TodoRestoreTests(unittest.TestCase):
    def setUp(self):
        self.sb, self.cleanup = sandbox_factory()
        self.addCleanup(self.cleanup)

    def run_restore(self, event=None, **kw):
        return self.sb.run_restore(event or start_event(), **kw)

    def parse_outcome(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_emits_allow_with_every_open_title(self):
        seed_issues(self.sb, 2, wip_number=2)
        out = self.parse_outcome(self.run_restore())
        self.assertEqual(out["outcome"], "allow")
        ctx = out["additional_context"]
        self.assertIn("Tracked item 01", ctx)
        self.assertIn("Tracked item 02", ctx)
        self.assertIn("#2 [in-progress] Tracked item 02", ctx)
        self.assertIn("todo_create", ctx)  # adoption instructions present

    def test_caps_at_30_with_more_suffix(self):
        seed_issues(self.sb, 31)
        out = self.parse_outcome(self.run_restore())
        ctx = out["additional_context"]
        self.assertIn("(+1 more open todos not shown", ctx)
        self.assertNotIn("Tracked item 31", ctx)
        self.assertIn("Tracked item 30", ctx)

    def test_empty_tracker_is_stated_cleanly(self):
        out = self.parse_outcome(self.run_restore())
        self.assertEqual(out["outcome"], "allow")
        self.assertIn("no open tracked todos", out["additional_context"])

    def test_writes_current_session_file(self):
        self.run_restore(start_event("sess-xyz"))
        with open(os.path.join(self.sb.state, "todo-session.current")) as fh:
            fields = fh.read().split(" ")
        self.assertEqual(fields[0], "sess-xyz")
        # second field is the daemon pid (0 when the ancestry walk fails,
        # as in tests — todo-sync then trusts the pointer)
        self.assertEqual(len(fields), 2)
        self.assertTrue(fields[1].isdigit())

    def test_session_file_written_even_when_gh_fails(self):
        """The session id is load-bearing for delete gating; it must be
        recorded before any network I/O (AC.5/AC.7 robustness)."""
        self.run_restore(start_event("sess-offline"),
                         env_extra={"GH_BIN": "/bin/false"})
        with open(os.path.join(self.sb.state, "todo-session.current")) as fh:
            self.assertEqual(fh.read().split(" ")[0], "sess-offline")

    def test_sabotaged_gh_fails_open_fast(self):
        t0 = time.monotonic()
        out = self.parse_outcome(
            self.run_restore(env_extra={"GH_BIN": "/bin/false"}))
        elapsed = time.monotonic() - t0
        self.assertEqual(out, {"outcome": "allow"})
        self.assertLess(elapsed, 5.0, "bare allow must not stall the session")

    def test_hanging_gh_times_out_within_budget(self):
        hang = os.path.join(self.sb.tmp, "hang-gh.sh")
        with open(hang, "w") as fh:
            fh.write("#!/usr/bin/env bash\nsleep 30\n")
        os.chmod(hang, 0o755)
        t0 = time.monotonic()
        out = self.parse_outcome(self.run_restore(
            env_extra={"GH_BIN": hang}, timeout=30))
        elapsed = time.monotonic() - t0
        self.assertEqual(out, {"outcome": "allow"})
        self.assertLess(elapsed, 8.0, "watchdog must kill a hung gh quickly")

    def test_cache_serves_last_good_list_marked_stale(self):
        seed_issues(self.sb, 1)
        self.run_restore()
        # GitHub goes away; the cached list must still reach the session.
        out = self.parse_outcome(
            self.run_restore(env_extra={"GH_BIN": "/bin/false"}))
        ctx = out["additional_context"]
        self.assertIn("Tracked item 01", ctx)
        self.assertIn("cached list", ctx)
        self.assertIn("possibly stale", ctx)

    def test_cache_refreshes_on_success(self):
        seed_issues(self.sb, 1)
        self.run_restore()
        seed_issues(self.sb, 2)
        out = self.parse_outcome(self.run_restore())
        self.assertIn("Tracked item 02", out["additional_context"])
        with open(os.path.join(self.sb.state, "todo-restore.cache")) as fh:
            self.assertEqual(len(json.load(fh)), 2)

    def test_missing_jq_fails_open(self):
        env = dict(self.sb.env)
        # Point PATH at an empty dir so jq cannot be found.
        empty = os.path.join(self.sb.tmp, "emptybin")
        os.makedirs(empty, exist_ok=True)
        env["PATH"] = empty
        out = self.parse_outcome(self.sb.run_restore(start_event(), env_extra=env))
        self.assertEqual(out, {"outcome": "allow"})


if __name__ == "__main__":
    unittest.main()
