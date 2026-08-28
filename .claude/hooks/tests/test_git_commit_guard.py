#!/usr/bin/env python3
"""git_commit_guard: what it decides, and what its refusal tells you to do.

CE-2.4. The guard had no tests at all, which is why nobody noticed its
protocol reminder never mentioned the board -- the one step that, when
skipped, is invisible: the prompt lands in chat, Patrick's queue says
"Nothing is waiting on you", and the checkpoint sits where he is not looking.

Run: python3 .claude/hooks/tests/test_git_commit_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GUARD = os.path.join(HOOKS, "git_commit_guard.py")


def run(command, cwd):
    p = subprocess.run(
        [sys.executable, GUARD],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}, "cwd": cwd}),
        capture_output=True, text=True, cwd=cwd)
    try:
        return json.loads(p.stdout)["hookSpecificOutput"]
    except Exception:
        return {"permissionDecision": "allow", "additionalContext": ""}


class GuardCase(unittest.TestCase):
    def repo_on(self, branch):
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", d], check=False))
        subprocess.run(["git", "init", "-q", "-b", branch, d], check=True)
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            subprocess.run(["git", "config", k, v], cwd=d, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=d, check=True)
        return d


class TestTheProtocolReminderNamesTheBoard(GuardCase):
    def test_a_develop_commit_is_told_to_post_the_checkpoint(self):
        """AC1. The command has to be IN the refusal. A reminder saying "use
        the board" without the invocation is one the reader has to go and look
        up, which is how it gets skipped under pressure."""
        out = run('git commit -m "chore: x"', self.repo_on("develop"))
        self.assertEqual(out["permissionDecision"], "ask")
        ctx = out.get("additionalContext", "")
        self.assertIn("ON THE BOARD", ctx)
        self.assertIn("ticket ask", ctx)
        self.assertIn("--audience patrick", ctx)

    def test_a_feature_branch_is_not_interrupted_at_all(self):
        """The control. Without it, "remind on everything" passes this file and
        the per-commit bottleneck the exemption exists to remove comes back."""
        out = run('git commit -m "feat(X-1): y"', self.repo_on("feature/x"))
        self.assertEqual(out["permissionDecision"], "allow")


if __name__ == "__main__":
    unittest.main(verbosity=2)
