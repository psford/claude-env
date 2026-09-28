#!/usr/bin/env python3
"""CE-2.111: park_before_toss_guard measures a loss in the repository that holds it.

Two defects, both reproduced before the fix:

- An rm of a file in another repository was measured in the SESSION's cwd.
  `git diff -- <path outside this repo>` exits 128, and since CE-2.110 an
  unknown loss refuses, so every such rm was refused. Before CE-2.110 the
  same call counted 0, and a large loss there passed unmeasured.
- `git status --porcelain` paths are relative to the repository root, and
  the guard joined them to the cwd. From a subdirectory every untracked file
  resolved to a path that does not exist, counted 0, and the loss was
  undercounted.

The CSO's list review (reviews/2026-09-28-ce2111-list-infosec.md) added:
pathspecs measured literally (F-L2), the hook's inherited GIT_* environment
kept out of git's discovery (F-L3), and the toplevel stripped (F-L6).

Each test drives the guard's real main() with a real payload, in real
temporary repositories. Each refusing case has a sibling that must pass.

Run: python3 .claude/hooks/tests/test_park_before_toss_cross_repo.py
"""
import os
import subprocess
import unittest
from unittest import mock

from test_fail_closed_batch1 import TempDirs, load, raising, run_guard

BIG, SMALL = 400, 3


def lines(path, count):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("".join(f"line {i}\n" for i in range(count)))


class TestCrossRepoRm(TempDirs):

    def setUp(self):
        self.guard = load("park_before_toss_guard")

    def test_an_rm_in_another_repo_is_measured_there(self):
        session, other = self.repo(), self.repo()
        small, big = os.path.join(other, "small.txt"), os.path.join(other, "big.txt")
        lines(small, SMALL)
        lines(big, BIG)
        code, err = run_guard(self.guard, f"rm {small}", session)
        self.assertEqual(code, 0, err)
        code, err = run_guard(self.guard, f"rm {big}", session)
        self.assertEqual(code, 2, err)
        self.assertIn("uncommitted", err)
        self.assertNotIn("cannot measure", err)

    def test_the_verdict_does_not_depend_on_the_session_cwd(self):
        other = self.repo()
        sub = os.path.join(other, "sub")
        big, small = os.path.join(other, "big.txt"), os.path.join(other, "small.txt")
        lines(big, BIG)
        lines(small, SMALL)
        lines(os.path.join(sub, "keep.txt"), 1)
        for cwd in (other, sub, self.repo()):
            with self.subTest(cwd=cwd):
                code, err = run_guard(self.guard, f"rm {big}", cwd)
                self.assertEqual(code, 2, err)
                code, err = run_guard(self.guard, f"rm {small}", cwd)
                self.assertEqual(code, 0, err)

    def test_an_unanswerable_target_repo_refuses_and_a_non_repo_target_passes(self):
        session, other = self.repo(), self.repo()
        target = os.path.join(other, "small.txt")
        lines(target, SMALL)
        with mock.patch.object(self.guard.subprocess, "run", raising("rev-parse")):
            code, err = run_guard(self.guard, f"rm {target}", session)
        self.assertEqual(code, 2, err)
        self.assertIn("cannot measure", err)
        # rc 0 with an empty toplevel is not an answer either.
        real = subprocess.run

        def empty_toplevel(args, *a, **kw):
            if "--show-toplevel" in args:
                return subprocess.CompletedProcess(args, 0, stdout="\n", stderr="")
            return real(args, *a, **kw)
        with mock.patch.object(self.guard.subprocess, "run", empty_toplevel):
            code, err = run_guard(self.guard, f"rm {target}", session)
        self.assertEqual(code, 2, err)
        self.assertIn("cannot measure", err)
        plain = self.tmp()
        outside = os.path.join(plain, "f.txt")
        lines(outside, BIG)
        code, err = run_guard(self.guard, f"rm {outside}", session)
        self.assertEqual(code, 0, err)

    def test_a_glob_character_name_is_measured_literally(self):
        other = self.repo()
        literal = os.path.join(other, "g[1]x.txt")
        lines(literal, BIG)
        lines(os.path.join(other, "g1x.txt"), SMALL)
        code, err = run_guard(self.guard, f"rm '{literal}'", self.repo())
        self.assertEqual(code, 2, err)
        # And the reverse: the small sibling is not charged with the big file.
        small_other = self.repo()
        lines(os.path.join(small_other, "g[1]x.txt"), SMALL)
        lines(os.path.join(small_other, "g1x.txt"), BIG)
        code, err = run_guard(self.guard,
                              f"rm '{os.path.join(small_other, 'g[1]x.txt')}'",
                              self.repo())
        self.assertEqual(code, 0, err)

    def test_inherited_git_environment_does_not_redirect_the_measurement(self):
        session, other, decoy = self.repo(), self.repo(), self.repo()
        big = os.path.join(other, "big.txt")
        lines(big, BIG)
        poisoned = {"GIT_DIR": os.path.join(decoy, ".git"), "GIT_WORK_TREE": decoy,
                    "GIT_INDEX_FILE": os.path.join(decoy, ".git", "index"),
                    "GIT_OBJECT_DIRECTORY": os.path.join(decoy, ".git", "objects")}
        with mock.patch.dict(os.environ, poisoned):
            code, err = run_guard(self.guard, f"rm {big}", session)
        self.assertEqual(code, 2, err)
        self.assertNotIn("cannot measure", err)
        # The change review's F1: a ceiling below the repository root makes
        # discovery answer "not a repo", which would measure 0 and pass.
        deep = os.path.join(other, "deep", "er")
        buried = os.path.join(deep, "big.txt")
        lines(buried, BIG)
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": os.path.join(other, "deep")}):
            code, err = run_guard(self.guard, f"rm {buried}", session)
        self.assertEqual(code, 2, err)


class TestSubdirectoryCwd(TempDirs):

    def setUp(self):
        self.guard = load("park_before_toss_guard")

    def test_untracked_files_are_counted_from_the_repository_root(self):
        for command in ("git clean -fd", "git restore ."):
            with self.subTest(command=command):
                repo = self.repo()
                sub = os.path.join(repo, "sub")
                lines(os.path.join(sub, "keep.txt"), 1)
                lines(os.path.join(repo, "elsewhere", "big.txt"), BIG)
                code, err = run_guard(self.guard, command, sub)
                self.assertEqual(code, 2, err)
                small = self.repo()
                small_sub = os.path.join(small, "sub")
                lines(os.path.join(small_sub, "keep.txt"), 1)
                lines(os.path.join(small, "elsewhere", "little.txt"), SMALL)
                code, err = run_guard(self.guard, command, small_sub)
                self.assertEqual(code, 0, err)


class TestSymlinkTargets(TempDirs):
    """CE-2.113. rm removes a symlink operand itself, never what it points
    to, so the loss is the link's own entry in the repository that holds the
    link. The guard used to follow the link: into the target's repository
    (git diff 128, a false refusal), into the target's lines (a link to a big
    file false-refused), and past a dangling link (skipped unmeasured)."""

    def setUp(self):
        self.guard = load("park_before_toss_guard")

    def test_a_link_to_a_directory_in_another_repo_is_measured_where_the_link_is(self):
        session, holder, target_repo = self.repo(), self.repo(), self.repo()
        target_dir = os.path.join(target_repo, "deps")
        lines(os.path.join(target_dir, "big.txt"), BIG)
        link = os.path.join(holder, "deps")
        os.symlink(target_dir, link)
        code, err = run_guard(self.guard, f"rm {link}", session)
        self.assertEqual(code, 0, err)
        # The directory itself, rm -r'd directly, is still measured and refused.
        code, err = run_guard(self.guard, f"rm -r {target_dir}", session)
        self.assertEqual(code, 2, err)

    def test_a_link_counts_as_one_line_not_its_targets_lines(self):
        session, holder = self.repo(), self.repo()
        big = os.path.join(holder, "big.txt")
        lines(big, BIG)
        link = os.path.join(holder, "big-link.txt")
        os.symlink(big, link)
        code, err = run_guard(self.guard, f"rm {link}", session)
        self.assertEqual(code, 0, err)
        code, err = run_guard(self.guard, f"rm {big}", session)
        self.assertEqual(code, 2, err)

    def test_a_dangling_link_is_measured_not_skipped(self):
        session, holder = self.repo(), self.repo()
        link = os.path.join(holder, "dangling")
        os.symlink(os.path.join(holder, "no-such-target"), link)
        code, err = run_guard(self.guard, f"rm {link}", session)
        self.assertEqual(code, 0, err)
        # Measured, so a git that cannot run for its repository refuses; a
        # skipped link would have passed without asking git anything.
        with mock.patch.object(self.guard.subprocess, "run", raising("rev-parse")):
            code, err = run_guard(self.guard, f"rm {link}", session)
        self.assertEqual(code, 2, err)
        self.assertIn("cannot measure", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
