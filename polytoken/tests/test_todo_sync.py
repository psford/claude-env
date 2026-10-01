"""Unit tests for polytoken/hooks/todo-sync.sh (fake gh via GH_BIN)."""

import json
import os
import subprocess
import unittest

from helpers import machine_name, sandbox_factory


def create_event(title, description="d"):
    return {"event": "post_tool_use", "tool_name": "todo_create",
            "input": {"title": title, "description": description}}


def update_event(todo_id, status=None, title=None):
    inp = {"id": todo_id}
    if status is not None:
        inp["status"] = status
    if title is not None:
        inp["title"] = title
    return {"event": "post_tool_use", "tool_name": "todo_update", "input": inp}


def complete_event(todo_id):
    return {"event": "post_tool_use", "tool_name": "todo_complete",
            "input": {"id": todo_id}}


def delete_event(todo_id):
    return {"event": "post_tool_use", "tool_name": "todo_delete",
            "input": {"id": todo_id}}


class TodoSyncTests(unittest.TestCase):
    def setUp(self):
        self.sb, self.cleanup = sandbox_factory()
        self.addCleanup(self.cleanup)
        self.machine = machine_name()

    # ------------------------------------------------------------ create
    def test_create_creates_labeled_issue_with_markers(self):
        r = self.sb.run_sync(create_event("Write the thing", "for the mac"))
        self.assertEqual(r.returncode, 0, r.stderr)
        issues = self.sb.issues()
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue["title"], "Write the thing")
        self.assertTrue(any(l.get("name") == "todo" for l in issue["labels"]),
                        issue["labels"])
        self.assertIn("session:%s" % self.sb.session_id, issue["body"])
        self.assertIn("machine:%s" % self.machine, issue["body"])
        self.assertIn("for the mac", issue["body"])

    def test_create_dedupes_same_title(self):
        self.sb.run_sync(create_event("Same title"))
        self.sb.run_sync(create_event("Same title"))
        self.assertEqual(len(self.sb.issues()), 1)
        self.assertTrue(any("dedupe" in l for l in self.sb.log_lines()))

    def test_back_to_back_same_title_creates_one_issue(self):
        """Two concurrent syncs must not both create — the lock serializes
        the list-then-mutate section (AC.3 batch pressure)."""
        env = self.sb.env
        procs = [
            subprocess.Popen(
                ["bash", os.path.join(self.sb.layer, "hooks", "todo-sync.sh")],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=env, text=True)
            for _ in range(2)
        ]
        for p in procs:
            p.communicate(json.dumps(create_event("Race title")))
        for p in procs:
            self.assertEqual(p.wait(), 0)
        self.assertEqual(len(self.sb.issues()), 1)
        creates = [c for c in self.sb.calls() if c.startswith("issue create")]
        self.assertEqual(len(creates), 1)

    # ---------------------------------------------------------- complete
    def test_complete_closes_issue(self):
        self.sb.seed_todo(1, "Finish it")
        self.sb.run_sync(create_event("Finish it"))
        r = self.sb.run_sync(complete_event(1))
        self.assertEqual(r.returncode, 0, r.stderr)
        issue = self.sb.issues()[0]
        self.assertEqual(issue["state"], "closed")

    def test_complete_without_mapping_logs_and_exits_zero(self):
        r = self.sb.run_sync(complete_event(42))
        self.assertEqual(r.returncode, 0)
        self.assertTrue(any("no title mapping" in l for l in self.sb.log_lines()))
        self.assertEqual(self.sb.issues(), [])

    # ------------------------------------------------------------ update
    def test_update_renames_issue(self):
        self.sb.seed_todo(1, "Old name")
        self.sb.run_sync(create_event("Old name"))
        r = self.sb.run_sync(update_event(1, title="New name"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sb.issues()[0]["title"], "New name")

    def test_update_status_transitions_labels(self):
        self.sb.seed_todo(1, "Labelled work")
        self.sb.run_sync(create_event("Labelled work"))
        self.sb.run_sync(update_event(1, status="in_progress"))
        labels_now = [l.get("name") for l in self.sb.issues()[0]["labels"]]
        self.assertIn("in-progress", labels_now)
        self.sb.run_sync(update_event(1, status="pending"))
        labels_now = [l.get("name") for l in self.sb.issues()[0]["labels"]]
        self.assertNotIn("in-progress", labels_now)
        self.assertIn("todo", labels_now)

    # ------------------------------------------------------------ delete
    def test_delete_of_created_closes_issue(self):
        self.sb.seed_todo(1, "Withdrawn work")
        self.sb.run_sync(create_event("Withdrawn work"))
        r = self.sb.run_sync(delete_event(1))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.sb.issues()[0]["state"], "closed")

    def test_delete_of_adopted_leaves_issue_open(self):
        self.sb.seed_todo(1, "Adopted work")
        self.sb.run_sync(create_event("Adopted work"))
        num = self.sb.issues()[0]["number"]
        self.sb.rewrite_issue(num, body="desc\n\nsession:earlier-session\nmachine:%s\ndate:2026-09-30" % self.machine)
        r = self.sb.run_sync(delete_event(1))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.sb.issues()[0]["state"], "open")
        self.assertTrue(any("adopted/foreign" in l for l in self.sb.log_lines()))

    def test_delete_cross_machine_leaves_issue_open(self):
        self.sb.seed_todo(1, "Other machine work")
        self.sb.run_sync(create_event("Other machine work"))
        num = self.sb.issues()[0]["number"]
        self.sb.rewrite_issue(num, body="desc\n\nsession:%s\nmachine:macbook\ndate:2026-09-30" % self.sb.session_id)
        self.sb.run_sync(delete_event(1))
        self.assertEqual(self.sb.issues()[0]["state"], "open")

    def test_delete_without_session_id_never_closes(self):
        self.sb.seed_todo(1, "Unknown session work")
        self.sb.run_sync(create_event("Unknown session work"))
        self.sb.clear_session()
        r = self.sb.run_sync(delete_event(1), env_extra={"POLYTOKEN_SESSION_ID": ""})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.sb.issues()[0]["state"], "open")
        self.assertTrue(any("never-close" in l for l in self.sb.log_lines()))

    def test_delete_unmapped_todo_is_noop(self):
        self.sb.seed_todo(1, "Kept work")
        self.sb.run_sync(create_event("Kept work"))
        r = self.sb.run_sync(delete_event(99))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.sb.issues()[0]["state"], "open")
        self.assertTrue(any("no title mapping" in l for l in self.sb.log_lines()))

    # ------------------------------------------------------------ hygiene
    def test_todo_list_is_free(self):
        """No gh call, no log line, immediate exit (AC.7)."""
        r = self.sb.run_sync({"event": "post_tool_use",
                              "tool_name": "todo_list", "input": {}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.sb.calls(), [])
        self.assertEqual(self.sb.log_lines(), [])

    def test_gh_failure_is_silent_to_session(self):
        r = self.sb.run_sync(create_event("Failing path"),
                             env_extra={"GH_BIN": "/bin/false"})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(self.sb.log_lines()), 1)
        lock = os.path.join(self.sb.state, "todo-sync.lockdir")
        self.assertFalse(os.path.exists(lock), "lockdir must not outlive the hook")

    def test_lock_released_after_success(self):
        self.sb.run_sync(create_event("Happy path"))
        lock = os.path.join(self.sb.state, "todo-sync.lockdir")
        self.assertFalse(os.path.exists(lock))

    def test_unknown_todo_tool_is_noop(self):
        r = self.sb.run_sync({"event": "post_tool_use",
                              "tool_name": "todo_nonsense", "input": {}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.sb.calls(), [])


if __name__ == "__main__":
    unittest.main()
