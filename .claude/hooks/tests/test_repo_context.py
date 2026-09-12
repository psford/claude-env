#!/usr/bin/env python3
"""Tests for _repo_context, which 31 hooks now depend on.

The fixture suite (run-hook-tests.sh) asserts a hook's exit code. That cannot
express "which repository did it look at", which is the whole question here --
so this is a unit test alongside it.

Run: python3 .claude/hooks/tests/test_repo_context.py
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _repo_context as rc  # noqa: E402


def make_repo(branch="feature/work", commit=True):
    path = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", branch, path], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=path, check=True)
    if commit:
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=path, check=True)
    return path


class TestTargetDirectory(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.repo], check=False))
        self.session = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.session], check=False))

    def test_no_command_returns_the_default(self):
        self.assertEqual(rc.target_directory("", default=self.session), self.session)

    def test_git_dash_C_wins(self):
        cmd = f"git -C {self.repo} commit -m x"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_cd_carries_to_later_statements(self):
        cmd = f"cd {self.repo} && git commit -m x"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_dash_C_beats_an_earlier_cd(self):
        other = make_repo()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", other], check=False))
        cmd = f"cd {other} && git -C {self.repo} commit -m x"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_unexpandable_variable_falls_back_rather_than_guessing(self):
        # The hook cannot expand $R. Falling back is conservative; inventing a
        # path would be worse than admitting ignorance.
        self.assertEqual(rc.target_directory('git -C "$R" commit -m x',
                                             default=self.session), self.session)

    def test_a_quoted_separator_does_not_split_the_statement(self):
        cmd = f'python3 -c "import os; os.chdir(1)" ; git -C {self.repo} commit -m x'
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    # ── CH-237.10: target_directory resolving the wrong repo ───────────────

    def test_a_dash_C_from_an_earlier_statement_does_not_win_over_a_tracked_cd(self):
        # `git -C other status` does not move the shell, so the push runs from
        # this repo. A -C that sticks to every later statement judges the push
        # against `other` -- a false negative wearing a resolved path.
        other = make_repo()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", other], check=False))
        cmd = f"cd {self.repo} && git -C {other} status && git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_a_dash_C_from_an_earlier_statement_does_not_smuggle_onto_a_later_push(self):
        # The twin: the -C belongs to the status, and the bare push after it
        # runs from the session repo. Judging it from the -C's repo approves
        # or blocks the wrong repository.
        cmd = f"git -C {self.repo} status; git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.session)

    def test_a_backgrounded_command_does_not_hide_the_cd_after_it(self):
        # A bare `&` separates statements in bash: the push really does run
        # from the cd'd repo.
        cmd = f": & cd {self.repo} && git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_a_cd_inside_a_subshell_moves_the_git_sharing_it(self):
        # Everything inside the parens runs after the cd, so the push runs
        # from the cd'd repo.
        cmd = f"(cd {self.repo} && git push origin main)"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_a_subshell_cd_does_not_escape_its_parens(self):
        # The other half of subshell semantics: once the parens close, the
        # shell is where it was. This push runs from the session.
        cmd = f"(cd {self.repo}) && git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.session)

    def test_pushd_moves_the_shell_like_cd(self):
        # pushd is a builtin that works non-interactively; it moves the shell
        # exactly as cd does.
        cmd = f"pushd {self.repo} && git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_a_glued_dash_C_path_is_honoured(self):
        # `-Cpath` is one token to shlex; an exact-token lookup never sees it.
        cmd = f"git -C{self.repo} push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)

    def test_an_attached_git_dir_value_names_the_work_tree(self):
        # This asserted the `.git` directory itself when first written, and
        # that value IS the bypass: `git rev-parse --show-toplevel` fails
        # outright inside a git dir, so every caller falls back to the session
        # and judges the wrong repo. Measured, not reasoned -- with `.git`
        # returned, `git --git-dir=<ios>/.git push` reached a repo with a
        # push-triggered macOS runner and the quota guard returned rc=0.
        #
        # The contract is "the directory the git commands will RUN in", and a
        # command carrying --git-dir runs in the work tree. So the work tree is
        # the answer, and the one predicate stays one predicate rather than 28
        # callers each learning what a `.git` suffix means.
        cmd = f"git --git-dir={self.repo}/.git push origin main"
        self.assertEqual(rc.target_directory(cmd, default=self.session),
                         self.repo)

    def test_work_tree_names_the_tree_being_judged(self):
        # GIT_GLOBAL_FLAGS_WITH_VALUE already counts --work-tree a
        # value-taking flag; target_directory omitting it is the sibling-list
        # drift this file warns about. The tree it names is the one judged.
        cmd = f"git --work-tree={self.repo} status"
        self.assertEqual(rc.target_directory(cmd, default=self.session), self.repo)


class TestEnterTargetRepo(unittest.TestCase):
    def setUp(self):
        self.origin = os.getcwd()
        self.addCleanup(lambda: os.chdir(self.origin))
        self.repo = make_repo()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.repo], check=False))

    def test_chdirs_into_the_target(self):
        payload = {"tool_input": {"command": f"git -C {self.repo} status"}, "cwd": self.origin}
        rc.enter_target_repo(payload)
        self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.repo))

    def test_falls_back_to_the_session_cwd(self):
        payload = {"tool_input": {"command": "git status"}, "cwd": self.repo}
        rc.enter_target_repo(payload)
        self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.repo))

    def test_survives_a_payload_with_no_command(self):
        rc.enter_target_repo({"cwd": self.repo})
        self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.repo))


class TestCurrentBranch(unittest.TestCase):
    def test_reports_a_normal_branch(self):
        repo = make_repo("feature/x")
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", repo], check=False))
        self.assertEqual(rc.current_branch(repo), "feature/x")

    def test_reports_an_unborn_branch(self):
        # rev-parse fails here; this is why a new repo's first commit broke.
        repo = make_repo("feature/y", commit=False)
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", repo], check=False))
        self.assertEqual(rc.current_branch(repo), "feature/y")

    def test_none_outside_a_work_tree(self):
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", d], check=False))
        self.assertIsNone(rc.current_branch(d))

    def test_detached_head_is_none_so_callers_fail_closed(self):
        repo = make_repo("main")
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", repo], check=False))
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                             capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True)
        self.assertIsNone(rc.current_branch(repo))


if __name__ == "__main__":
    unittest.main(verbosity=2)
