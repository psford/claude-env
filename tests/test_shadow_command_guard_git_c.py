#!/usr/bin/env python3
"""shadow_command_guard judges a git -C statement's own paths inside its -C
directory (CE-2.76).

The cases are fixtures 30 to 33 in .claude/hooks/tests/shadow_command_guard/,
run through that suite's own driver, so each case exists once. These tests
exist because `ticket check` can name a unittest and cannot run a .md
fixture, and Clyde, which used to record fixture checks, was retired on
2026-09-20.

Fixtures 30 and 31 were refused before the fix: a restore of a test file that
exists in another repo, from a session with no tests root, was read as a new
test root under the session. 32 and 33 pin what must stay refused.
"""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join(ROOT, ".claude", "hooks", "tests", "shadow_command_guard")
HOOK = os.path.join(ROOT, ".claude", "hooks", "shadow_command_guard.py")


def run_fixture(name):
    """The suite's driver on one fixture: exit 0 when the hook's verdict
    matches the PASS or BLOCK in the fixture's name."""
    expect = "BLOCK" if name.endswith(".BLOCK.md") else "PASS"
    return subprocess.run(
        ["bash", os.path.join(SUITE, "_invoke.sh"), os.path.join(SUITE, name),
         HOOK, expect],
        capture_output=True, text=True, timeout=60)


class TestGitCResolvesItsOwnPaths(unittest.TestCase):

    def assertFixtureHolds(self, name):
        proc = run_fixture(name)
        self.assertEqual(proc.returncode, 0,
                         f"{name}: {proc.stdout}{proc.stderr}")

    def test_a_git_C_restore_of_an_existing_test_file_is_allowed(self):
        self.assertFixtureHolds(
            "30-git-C-names-the-repo-its-paths-are-in.PASS.md")

    def test_the_same_restore_through_a_variable_is_allowed(self):
        self.assertFixtureHolds("31-git-C-through-a-variable.PASS.md")

    def test_a_new_tests_root_inside_the_C_directory_is_still_refused(self):
        self.assertFixtureHolds(
            "32-a-new-tests-root-inside-the-git-C-directory.BLOCK.md")

    def test_a_redirect_stays_in_the_shell_directory(self):
        self.assertFixtureHolds(
            "33-a-redirect-in-a-git-C-statement-stays-in-the-shell-directory.BLOCK.md")


if __name__ == "__main__":
    unittest.main()
