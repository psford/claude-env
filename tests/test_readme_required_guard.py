#!/usr/bin/env python3
"""readme_required_guard: a feature PR ships its README update.

Three checks. The fixture suite (.claude/hooks/tests/readme_required_guard/)
runs through its _invoke.sh, and every case there must come out as its file
name says. The fixtures judge exit codes only, so the second check reads what a
refusal says: it has to name the branch, the line count and the files, and tell
the reader what to do (specs/guards.md, "Refusal messages"). The third is the
fail-open hole a cold review found on 2026-11-10: input the hook can't read,
when it opens a PR, is refused rather than let through.

Run: python3 tests/test_readme_required_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "readme_required_guard.py")
RUNNER = os.path.join(ROOT, ".claude", "hooks", "tests", "run-hook-tests.sh")
PR = "gh pr create --base develop --title x --body y"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def hook(stdin):
    return subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True,
                          text=True, timeout=60, cwd=tempfile.gettempdir())


class FixtureSuite(unittest.TestCase):
    def test_every_fixture_comes_out_as_named(self):
        out = subprocess.run(["bash", RUNNER, "readme_required_guard"], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("ALL 25 HOOK TESTS PASSED", out.stdout)


class RefusalMessage(unittest.TestCase):
    def test_it_names_the_branch_the_count_and_the_fix(self):
        with tempfile.TemporaryDirectory() as repo:
            git(repo, "init", "-q")
            git(repo, "config", "user.email", "t@e")
            git(repo, "config", "user.name", "t")
            with open(os.path.join(repo, "README.md"), "w") as f:
                f.write("baseline\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "baseline")
            git(repo, "update-ref", "refs/remotes/origin/develop", "HEAD")
            git(repo, "checkout", "-q", "-b", "feature/x")
            os.makedirs(os.path.join(repo, "src"))
            with open(os.path.join(repo, "src", "app.mjs"), "w") as f:
                f.write("".join(f"export const x{i} = {i};\n" for i in range(60)))
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "feat: new code")
            out = hook(json.dumps({"tool_name": "Bash", "cwd": repo, "tool_input": {"command": PR}}))
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertIn("feature/x changes 60 lines of code", out.stderr)
        self.assertIn("src/app.mjs (60)", out.stderr)
        self.assertIn("leaves the README untouched", out.stderr)
        self.assertIn("Update the README on feature/x", out.stderr)


class FailsClosed(unittest.TestCase):
    def test_unreadable_input_that_opens_a_pr_is_refused(self):
        for stdin in (f"not json at all: {PR}", json.dumps([PR])):
            out = hook(stdin)
            self.assertEqual(out.returncode, 2, f"{stdin!r}: {out.stderr}")
            self.assertIn("can't be judged", out.stderr)

    def test_unreadable_input_that_opens_nothing_passes(self):
        self.assertEqual(hook("not json, and no PR").returncode, 0)


if __name__ == "__main__":
    unittest.main()
