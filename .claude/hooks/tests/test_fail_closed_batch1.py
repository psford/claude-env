#!/usr/bin/env python3
"""CE-2.102, batch 1: three wired, blocking guards refuse when they cannot decide.

Each of these guards treated a failed git or ticket call as "nothing to judge"
and allowed the command. The CSO's list review of CE-2.102
(reviews/2026-09-27-ce2102-list-infosec.md, F0-F2) reproduced each one:

- shared_rules_link_guard: git rev-parse raising read as "not a repo".
- pr_after_accept_guard: a ticket show that failed read as "no ticket".
- park_before_toss_guard: a git that failed measured the loss as 0.

Each test drives the guard's real main() with a real payload on stdin. The
failure is injected by replacing subprocess.run inside the guard's module
only. Each refusing case has a sibling that must still pass, so a guard
that refused everything would fail the suite.

Run: python3 .claude/hooks/tests/test_fail_closed_batch1.py
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HOOKS)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HOOKS, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_guard(module, command, cwd):
    """(exit code, stderr) of the guard's main() on a Bash payload."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
    err = io.StringIO()
    env = {k: v for k, v in os.environ.items()
           if k not in ("PARK_OK", "PARK_MIN_LINES")}
    with mock.patch.object(sys, "stdin", io.StringIO(payload)), \
            mock.patch.object(sys, "stderr", err), \
            mock.patch.dict(os.environ, env, clear=True):
        code = module.main()
    return code, err.getvalue()


def raising(match, exc=OSError("injected: git cannot run")):
    """A subprocess.run that raises for argv containing `match`, else runs."""
    real = subprocess.run

    def fake(args, *a, **kw):
        if match in " ".join(map(str, args)):
            raise exc
        return real(args, *a, **kw)
    return fake


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TempDirs(unittest.TestCase):

    def tmp(self):
        path = tempfile.mkdtemp(prefix="ce2102-")
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def repo(self):
        path = self.tmp()
        git(path, "init", "-q", "-b", "develop")
        git(path, "config", "user.email", "t@example.test")
        git(path, "config", "user.name", "t")
        with open(os.path.join(path, "a.txt"), "w") as fh:
            fh.write("one\n")
        git(path, "add", "a.txt")
        git(path, "commit", "-q", "-m", "base")
        return path


class TestSharedRulesLinkGuard(TempDirs):

    def setUp(self):
        self.guard = load("shared_rules_link_guard")

    def test_a_git_that_cannot_run_refuses(self):
        for exc in (OSError("injected: no git"),
                    subprocess.TimeoutExpired(["git"], 5)):
            with self.subTest(exc=type(exc).__name__):
                cwd = self.repo()
                with mock.patch.object(self.guard.subprocess, "run",
                                       raising("rev-parse", exc)):
                    code, err = run_guard(self.guard, "git commit -m x", cwd)
                self.assertEqual(code, 2, err)
                self.assertIn("git", err)
        # F7: a cwd that does not exist raises inside subprocess.run.
        code, err = run_guard(self.guard, "git commit -m x", "/nonexistent-ce2102-cwd")
        self.assertEqual(code, 2, err)

    def test_a_real_non_repo_still_passes(self):
        code, err = run_guard(self.guard, "git commit -m x", self.tmp())
        self.assertEqual(code, 0, err)


class TestPrAfterAcceptGuard(TempDirs):

    def setUp(self):
        self.guard = load("pr_after_accept_guard")
        self.command = 'gh pr create --title "CE-2.102: a change" --body "b"'

    def _completed(self, rc, out):
        return subprocess.CompletedProcess(["ticket"], rc, stdout=out, stderr="boom")

    def test_an_unreadable_ticket_refuses_the_pr(self):
        cases = {
            "raises": mock.Mock(side_effect=OSError("injected: no ticket CLI")),
            "exits non-zero": mock.Mock(return_value=self._completed(1, "")),
            "prints non-JSON": mock.Mock(return_value=self._completed(0, "not json")),
        }
        for name, fake in cases.items():
            with self.subTest(name):
                with mock.patch.object(self.guard.subprocess, "run", fake):
                    code, err = run_guard(self.guard, self.command, self.tmp())
                self.assertEqual(code, 2, f"{name}: {err}")
                self.assertIn("CE-2.102", err)

    def test_an_id_that_is_not_a_ticket_here_still_passes(self):
        """ticket_ids matches wide on purpose (a title saying sha256 or UTF-8
        yields a false id), so the two answers meaning "not a ticket here"
        still pass. Their text is the ticket CLI's, measured 2026-09-28."""
        for stderr in ("ticket: no such ticket: CE-2.102",
                       "ticket: CE-2.102 is not from this repo's numbering, which issues CH- ids."):
            with self.subTest(stderr=stderr):
                fake = mock.Mock(return_value=subprocess.CompletedProcess(
                    ["ticket"], 1, stdout="", stderr=stderr))
                with mock.patch.object(self.guard.subprocess, "run", fake):
                    code, err = run_guard(self.guard, self.command, self.tmp())
                self.assertEqual(code, 0, err)

    def test_an_accepted_ticket_still_opens(self):
        fake = mock.Mock(return_value=self._completed(
            0, json.dumps({"status": "accepted", "ongoing": False})))
        with mock.patch.object(self.guard.subprocess, "run", fake):
            code, err = run_guard(self.guard, self.command, self.tmp())
        self.assertEqual(code, 0, err)


class TestParkBeforeTossGuard(TempDirs):

    def setUp(self):
        self.guard = load("park_before_toss_guard")

    def _big_change(self, cwd, lines=400):
        with open(os.path.join(cwd, "a.txt"), "w") as fh:
            fh.write("".join(f"line {i}\n" for i in range(lines)))

    def test_an_unmeasurable_loss_refuses(self):
        for command in ("git restore .", "git clean -fd"):
            for step in ("diff", "status"):
                with self.subTest(command=command, step=step):
                    cwd = self.repo()
                    self._big_change(cwd, lines=3)  # small: only an unknown loss refuses
                    with mock.patch.object(self.guard.subprocess, "run", raising(step)):
                        code, err = run_guard(self.guard, command, cwd)
                    self.assertEqual(code, 2, err)
                    self.assertIn("cannot measure", err)

    def test_an_rm_whose_repo_check_raised_refuses(self):
        cwd = self.repo()
        self._big_change(cwd, lines=3)
        with mock.patch.object(self.guard.subprocess, "run", raising("rev-parse")):
            code, err = run_guard(self.guard, "rm a.txt", cwd)
        self.assertEqual(code, 2, err)
        self.assertIn("cannot measure", err)

    def test_measurable_small_losses_and_non_repo_rm_still_pass(self):
        cwd = self.repo()
        self._big_change(cwd, lines=3)
        code, err = run_guard(self.guard, "git restore .", cwd)
        self.assertEqual(code, 0, err)
        plain = self.tmp()
        with open(os.path.join(plain, "f.txt"), "w") as fh:
            fh.write("x\n" * 400)
        code, err = run_guard(self.guard, "rm f.txt", plain)
        self.assertEqual(code, 0, err)
        # The existing judgment is unchanged: a large measured loss still refuses.
        self._big_change(cwd, lines=400)
        code, err = run_guard(self.guard, "git restore .", cwd)
        self.assertEqual(code, 2, err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
