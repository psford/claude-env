#!/usr/bin/env python3
"""Does the working-tree guard notice a subagent that wandered into another repo?

The fixture suite drives one scratch repo, which cannot express the question
this pair exists to answer: a subagent editing a *sibling* repository while the
session sits elsewhere. Until 2026-08-08 the answer was no -- both hooks looked
only at the session's cwd, so wander anywhere else was invisible.

Run: python3 .claude/hooks/tests/test_agent_workspace_guard.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SNAPSHOT = os.path.join(HOOKS, "agent_working_tree_snapshot.py")
GUARD = os.path.join(HOOKS, "agent_working_tree_guard.py")


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.parent = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.parent], check=False))
        self.session = self.make_repo("session")
        self.sibling = self.make_repo("sibling")
        # Pin discovery to this scratch parent so the test never depends on
        # whatever happens to live in ~/projects.
        self.env = {**os.environ, "CLAUDE_WORKSPACE_ROOTS": self.parent}
        self.payload = {
            "tool_name": "Agent",
            "session_id": "test-session",
            "tool_input": {"prompt": "do a thing", "subagent_type": "Explore"},
            "cwd": self.session,
        }

    def make_repo(self, name):
        path = os.path.join(self.parent, name)
        os.makedirs(path)
        subprocess.run(["git", "init", "-q", "-b", "main", path], check=True)
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            subprocess.run(["git", "config", k, v], cwd=path, check=True)
        with open(os.path.join(path, "README.md"), "w") as fh:
            fh.write("baseline\n")
        subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)
        return path

    def run_hook(self, script):
        p = subprocess.run([sys.executable, script], input=json.dumps(self.payload),
                           capture_output=True, text=True, cwd=self.session, env=self.env)
        return p.stdout

    def dirty(self, repo, name="wandered.txt"):
        with open(os.path.join(repo, name), "w") as fh:
            fh.write("written by a subagent\n")

    def guard_report(self):
        out = self.run_hook(GUARD)
        if not out.strip():
            return None
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]


class TestSiblingRepoWander(WorkspaceCase):
    def test_change_in_a_sibling_repo_is_reported(self):
        self.run_hook(SNAPSHOT)
        self.dirty(self.sibling)
        report = self.guard_report()
        self.assertIsNotNone(report, "wander into a sibling repo went unreported")
        self.assertIn(self.sibling, report)
        self.assertIn("wandered.txt", report)

    def test_change_in_the_session_repo_still_reported(self):
        self.run_hook(SNAPSHOT)
        self.dirty(self.session)
        report = self.guard_report()
        self.assertIsNotNone(report)
        self.assertIn(self.session, report)

    def test_both_repos_reported_together(self):
        self.run_hook(SNAPSHOT)
        self.dirty(self.session, "a.txt")
        self.dirty(self.sibling, "b.txt")
        report = self.guard_report()
        self.assertIn(self.session, report)
        self.assertIn(self.sibling, report)
        self.assertIn("2 repo(s)", report)

    def test_clean_workspace_stays_silent(self):
        self.run_hook(SNAPSHOT)
        self.assertIsNone(self.guard_report())

    def test_dirt_predating_the_agent_is_not_blamed_on_it(self):
        # The delta must work per repo, not just for the session's.
        self.dirty(self.sibling, "pre-existing.txt")
        self.run_hook(SNAPSHOT)
        self.assertIsNone(self.guard_report())

    def test_pre_existing_plus_new_reports_only_the_new(self):
        self.dirty(self.sibling, "pre-existing.txt")
        self.run_hook(SNAPSHOT)
        self.dirty(self.sibling, "new.txt")
        report = self.guard_report()
        self.assertIn("new.txt", report)
        self.assertNotIn("pre-existing.txt", report)

    def test_missing_snapshot_falls_back_to_reporting_everything(self):
        self.dirty(self.sibling)
        report = self.guard_report()  # no snapshot run at all
        self.assertIsNotNone(report)
        self.assertIn("no pre-call snapshot", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
