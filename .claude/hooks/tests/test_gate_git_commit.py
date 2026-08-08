#!/usr/bin/env python3
"""The commit gate must interrupt for ad-hoc work and stay out of the way of
ticket-driven work.

A gate that fires where it cannot inform the decision trains people to click
through it. In a five-story epic the prompt would fire five times on commits
Patrick has no context on -- so it is skipped exactly when a ticket has already
asserted what the prompt would have asked.

Run: python3 .claude/hooks/tests/test_gate_git_commit.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GATE = os.path.join(HOOKS, "gate_git_commit.py")
MAIN_GUARD = os.path.join(HOOKS, "main_branch_guard.py")


def decision(hook, command, cwd):
    p = subprocess.run(
        [sys.executable, hook],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}),
        capture_output=True, text=True, cwd=cwd)
    if hook == MAIN_GUARD:
        return "block" if p.returncode == 2 else "allow"
    try:
        return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return f"unparseable: {p.stdout!r} {p.stderr!r}"


class GateCase(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.repo], check=False))
        subprocess.run(["git", "init", "-q", "-b", "feature/x", self.repo], check=True)
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            subprocess.run(["git", "config", k, v], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=self.repo, check=True)

    def add_store(self, prefix="PP"):
        store = os.path.join(self.repo, ".claude", "tickets")
        os.makedirs(store, exist_ok=True)
        with open(os.path.join(store, "config.json"), "w") as fh:
            json.dump({"prefix": prefix}, fh)
        return store

    def add_ticket(self, tid, status):
        store = os.path.join(self.repo, ".claude", "tickets")
        with open(os.path.join(store, f"{tid}.json"), "w") as fh:
            json.dump({"id": tid, "status": status}, fh)

    def gate(self, command):
        return decision(GATE, command, self.repo)


class TestTicketDrivenCommitsAreNotInterrupted(GateCase):
    def test_in_progress_ticket_on_a_feature_branch_is_allowed(self):
        self.add_store()
        self.add_ticket("PP-3", "in_progress")
        self.assertEqual(self.gate('git commit -m "feat(PP-3): the thing"'), "allow")

    def test_heredoc_message_naming_the_ticket_is_allowed(self):
        self.add_store()
        self.add_ticket("PP-3", "in_progress")
        cmd = "git commit -q -F - <<'EOF'\nfeat(PP-3): via heredoc\n\nbody\nEOF"
        self.assertEqual(self.gate(cmd), "allow")


class TestEverythingElseStillPrompts(GateCase):
    def test_no_ticket_store_still_prompts(self):
        self.assertEqual(self.gate('git commit -m "ad-hoc work"'), "ask")

    def test_ticket_in_the_wrong_state_still_prompts(self):
        self.add_store()
        self.add_ticket("PP-3", "draft")
        self.assertEqual(self.gate('git commit -m "feat(PP-3): too early"'), "ask")

    def test_unnamed_ticket_still_prompts(self):
        self.add_store()
        self.add_ticket("PP-3", "in_progress")
        self.assertEqual(self.gate('git commit -m "forgot to name it"'), "ask")

    def test_nonexistent_ticket_still_prompts(self):
        self.add_store()
        self.assertEqual(self.gate('git commit -m "feat(PP-99): invented"'), "ask")

    def test_trunk_still_prompts(self):
        subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=self.repo, check=True)
        self.add_store()
        self.add_ticket("PP-3", "in_progress")
        self.assertEqual(self.gate('git commit -m "feat(PP-3): on trunk"'), "ask")


class TestCommitDetectionIsTokenBased(GateCase):
    def test_a_branch_named_after_commits_is_not_a_commit(self):
        # This exact command was blocked on 2026-08-08: the branch name
        # contains "commit", and the rule matched the whole string.
        self.assertEqual(self.gate("git checkout -q -b fix/commit-gate-respects-tickets"), "allow")

    def test_a_message_quoting_the_word_is_not_a_commit(self):
        self.assertEqual(self.gate('git log --grep "commit gate"'), "allow")

    def test_dash_C_before_the_subcommand_is_still_a_commit(self):
        self.assertEqual(self.gate(f'git -C {self.repo} commit -m "ad-hoc"'), "ask")

    def test_unrelated_commands_pass(self):
        self.assertEqual(self.gate("ls -la"), "allow")


class TestMainBranchGuardSharesTheFix(GateCase):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=self.repo, check=True)

    def test_branch_name_containing_commit_is_not_blocked_on_main(self):
        self.assertEqual(
            decision(MAIN_GUARD, "git checkout -q -b fix/commit-gate", self.repo), "allow")

    def test_a_real_commit_on_main_is_still_blocked(self):
        self.assertEqual(
            decision(MAIN_GUARD, 'git commit -m "x"', self.repo), "block")


if __name__ == "__main__":
    unittest.main(verbosity=2)
