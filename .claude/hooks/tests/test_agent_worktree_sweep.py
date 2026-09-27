#!/usr/bin/env python3
"""Test agent_worktree_sweep.py, the SessionStart hook that removes an agent's
isolation worktree once the session holding it has ended (CE-2.53).

Measured on Claude Code 2.1.270 (CE-2.53's description): an agent worktree
sits at <main>/.claude/worktrees/agent-<id> on branch worktree-agent-<id>,
and while its agent runs it is locked with the reason
"claude agent agent-<id> (pid <pid> start <ticks>)", where <ticks> is field
22 of /proc/<pid>/stat. Each test builds a real repository and real
worktrees in a temp dir, locks them in that exact shape, and drives the real
hook as a subprocess with a SessionStart payload on stdin.

A "running" holder is this test process: its own pid and its own start time.
An "ended" holder is a pid/start pair no live process has -- this process's
pid with a start time one tick off, or a pid above the kernel's pid_max.

Run: python3 .claude/hooks/tests/test_agent_worktree_sweep.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HOOK = os.path.join(HOOKS, "agent_worktree_sweep.py")

GIT_ENV = {
    k: v for k, v in os.environ.items()
    if not k.startswith("GIT_")
}
GIT_ENV.update({
    "GIT_AUTHOR_NAME": "sweep-test",
    "GIT_AUTHOR_EMAIL": "sweep-test@example.invalid",
    "GIT_COMMITTER_NAME": "sweep-test",
    "GIT_COMMITTER_EMAIL": "sweep-test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
})

# Above the kernel's largest pid_max (2**22), so no process can hold it.
NO_SUCH_PID = 2 ** 22 + 7


def _git(cwd, *args):
    result = subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True, text=True, env=GIT_ENV, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {args} failed: {result.stderr}")
    return result.stdout


def _own_start_ticks():
    with open(f"/proc/{os.getpid()}/stat", encoding="utf-8") as fh:
        fields = fh.read().rsplit(")", 1)[1].split()
    return int(fields[19])


def _lock_reason(agent_id, pid, start):
    return f"claude agent agent-{agent_id} (pid {pid} start {start})"


def _age(path, seconds):
    """Back-date a worktree's .git file, which is what the hook reads as the
    worktree's age."""
    then = time.time() - seconds
    os.utime(os.path.join(path, ".git"), (then, then))


class TestWorktreesDoNotOutliveTheirAgent(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.repo = os.path.join(self.root, "repo")
        os.makedirs(self.repo)
        _git(self.repo, "init", "-q", "-b", "develop")
        with open(os.path.join(self.repo, "README"), "w", encoding="utf-8") as fh:
            fh.write("probe\n")
        _git(self.repo, "add", "README")
        _git(self.repo, "commit", "-q", "-m", "init")

    def tearDown(self):
        # Worktrees register themselves in the repo's own .git, so the whole
        # temp dir goes with them.
        self._tmp.cleanup()

    def _agent_worktree(self, agent_id, lock_reason=None):
        path = os.path.join(self.repo, ".claude", "worktrees", f"agent-{agent_id}")
        _git(self.repo, "worktree", "add", "-q", "-b",
             f"worktree-agent-{agent_id}", path)
        if lock_reason is not None:
            _git(self.repo, "worktree", "lock", "--reason", lock_reason, path)
        return path

    def _registered(self):
        """{path: lock reason or None} for every worktree but the main one."""
        out = _git(self.repo, "worktree", "list", "--porcelain")
        found = {}
        for block in out.strip().split("\n\n"):
            lines = block.splitlines()
            path = lines[0][len("worktree "):]
            if os.path.realpath(path) == os.path.realpath(self.repo):
                continue
            reason = None
            for line in lines[1:]:
                if line == "locked":
                    reason = ""
                elif line.startswith("locked "):
                    reason = line[len("locked "):]
            found[os.path.realpath(path)] = reason
        return found

    def _sweep(self, cwd=None, stdin=None):
        if stdin is None:
            stdin = json.dumps({
                "hook_event_name": "SessionStart",
                "cwd": cwd or self.repo,
                "session_id": "sweep-test",
            })
        return subprocess.run(
            [sys.executable, HOOK],
            input=stdin, capture_output=True, text=True,
            cwd=cwd or self.repo, env=GIT_ENV, timeout=60,
        )

    # --- AC1 -------------------------------------------------------------

    def test_a_worktree_for_an_ended_agent_is_removed(self):
        start = _own_start_ticks()
        reused_pid = self._agent_worktree(
            "a1111111111111111",
            _lock_reason("a1111111111111111", os.getpid(), start + 1),
        )
        gone_pid = self._agent_worktree(
            "a2222222222222222",
            _lock_reason("a2222222222222222", NO_SUCH_PID, start),
        )

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        for path in (reused_pid, gone_pid):
            self.assertNotIn(os.path.realpath(path), registered, result.stdout)
            self.assertFalse(os.path.exists(path), f"{path} still on disk")
        # Removing the worktree keeps its branch, so no commit is lost.
        branches = _git(self.repo, "branch", "--list", "worktree-agent-*")
        self.assertIn("worktree-agent-a1111111111111111", branches)
        self.assertIn("worktree-agent-a2222222222222222", branches)

    def test_a_worktree_for_a_running_agent_is_left_alone(self):
        reason = _lock_reason("a3333333333333333", os.getpid(), _own_start_ticks())
        path = self._agent_worktree("a3333333333333333", reason)

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._registered().get(os.path.realpath(path)), reason)
        self.assertTrue(os.path.isdir(path))

    # --- AC2 -------------------------------------------------------------

    def test_a_dirty_worktree_survives_the_sweep_and_is_named(self):
        start = _own_start_ticks()
        untracked = self._agent_worktree(
            "a4444444444444444",
            _lock_reason("a4444444444444444", NO_SUCH_PID, start),
        )
        with open(os.path.join(untracked, "notes.txt"), "w", encoding="utf-8") as fh:
            fh.write("work an agent left behind\n")
        modified = self._agent_worktree(
            "a5555555555555555",
            _lock_reason("a5555555555555555", NO_SUCH_PID, start),
        )
        with open(os.path.join(modified, "README"), "a", encoding="utf-8") as fh:
            fh.write("changed\n")

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        for path in (untracked, modified):
            self.assertIn(os.path.realpath(path), registered)
            self.assertTrue(os.path.isdir(path))
            self.assertIn(path, result.stdout)
        with open(os.path.join(untracked, "notes.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "work an agent left behind\n")

    # --- the edges the description names -----------------------------------

    def test_a_lock_it_cannot_read_is_left_alone(self):
        odd = self._agent_worktree("a6666666666666666", "held by someone else")
        bare = self._agent_worktree("a7777777777777777", "")

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        self.assertIn(os.path.realpath(odd), registered)
        self.assertIn(os.path.realpath(bare), registered)

    def test_an_unlocked_clean_worktree_is_removed_only_once_it_is_old(self):
        young = self._agent_worktree("a8888888888888888")
        old = self._agent_worktree("a9999999999999999")
        _age(old, 3600)

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        self.assertIn(os.path.realpath(young), registered)
        self.assertNotIn(os.path.realpath(old), registered)

    def test_a_worktree_outside_the_agent_folder_is_never_touched(self):
        named = os.path.join(self.root, "repo--CE-1")
        _git(self.repo, "worktree", "add", "-q", "-b", "dev/CE-1", named)
        _age(named, 3600)
        stray = os.path.join(self.repo, ".claude", "worktrees", "not-an-agent")
        _git(self.repo, "worktree", "add", "-q", "-b", "stray", stray)
        _age(stray, 3600)
        nested = os.path.join(
            self.repo, ".claude", "worktrees", "deeper", "agent-ab0000000000000000"
        )
        _git(self.repo, "worktree", "add", "-q", "-b", "nested", nested)
        _age(nested, 3600)

        result = self._sweep()

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        for path in (named, stray, nested):
            self.assertIn(os.path.realpath(path), registered)

    def test_a_session_started_in_a_worktree_sweeps_the_main_checkout(self):
        named = os.path.join(self.root, "repo--CE-2")
        _git(self.repo, "worktree", "add", "-q", "-b", "dev/CE-2", named)
        ended = self._agent_worktree(
            "ac000000000000000",
            _lock_reason("ac000000000000000", NO_SUCH_PID, _own_start_ticks()),
        )

        result = self._sweep(cwd=named)

        self.assertEqual(result.returncode, 0, result.stderr)
        registered = self._registered()
        self.assertNotIn(os.path.realpath(ended), registered)
        self.assertIn(os.path.realpath(named), registered)

    def test_bad_input_or_no_repository_exits_0_and_removes_nothing(self):
        ended = self._agent_worktree(
            "ad000000000000000",
            _lock_reason("ad000000000000000", NO_SUCH_PID, _own_start_ticks()),
        )
        outside = os.path.join(self.root, "not-a-repo")
        os.makedirs(outside)

        not_json = self._sweep(stdin="{not json")
        no_repo = self._sweep(cwd=outside)

        self.assertEqual(not_json.returncode, 0, not_json.stderr)
        self.assertEqual(no_repo.returncode, 0, no_repo.stderr)
        self.assertIn(os.path.realpath(ended), self._registered())


if __name__ == "__main__":
    unittest.main()
