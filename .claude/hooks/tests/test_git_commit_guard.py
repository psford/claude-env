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


def decision(command, cwd):
    """The hook's decision, with SILENCE distinguishable from a grant.

    CH-237.6. `run()` above answers "allow" when the hook printed nothing,
    which is the very conflation this guard's bug was made of: an active grant
    that suppresses the prompt reads the same to it as abstaining. Any test
    about whether the hook decided at all has to see the difference, so this
    returns None for silence.

    It also means test_a_feature_branch_is_not_interrupted_at_all, which uses
    `run()`, would pass whether the hook grants or says nothing. Left alone
    here -- rewriting a neighbouring test is not this story -- but it is not
    evidence of a grant.
    """
    p = subprocess.run(
        [sys.executable, GUARD],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}, "cwd": cwd}),
        capture_output=True, text=True, cwd=cwd)
    if not p.stdout.strip():
        return None
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]


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


class TestItDecidesOnlyAboutCommits(GuardCase):
    """CH-237.6 (Grace F3). The trigger was `\\bgit\\b.*\\bcommit\\b` -- the two
    words anywhere, in that order -- so the hook issued permission decisions for
    commands it had never identified.

    On a feature branch that meant permissionDecision "allow", an ACTIVE grant
    that suppresses the prompt, for things that are not commits at all. On
    develop it meant "ask", which a subagent cannot answer, so a dispatched
    agent could not run any check whose payload merely named a git command.

    Silence is the right answer for a command this hook is not about: it leaves
    the decision to the hook that can identify one, and to the ordinary
    permission system.
    """

    NOT_COMMITS = (
        'git log --grep commit',
        'git checkout -b fix/commit-gate',
        'echo "remember to git commit later"',
        'printf %s (a payload naming git commit) | python3 hook.py',
    )

    def test_a_command_that_only_names_the_words_draws_no_decision(self):
        # On a FEATURE branch, because that is where the old regex granted
        # rather than merely prompted -- the more dangerous half.
        feature = self.repo_on("feature/x")
        for command in self.NOT_COMMITS:
            with self.subTest(command=command):
                self.assertIsNone(
                    decision(command, feature),
                    f"the hook issued a decision for {command!r}, which is not "
                    f"a commit")

    def test_the_same_holds_on_develop(self):
        # And on develop, because an `ask` a subagent cannot answer is a block.
        develop = self.repo_on("develop")
        for command in self.NOT_COMMITS:
            with self.subTest(command=command):
                self.assertIsNone(
                    decision(command, develop),
                    f"the hook issued a decision for {command!r} on develop; a "
                    f"dispatched agent cannot answer an ask")

    def test_a_real_commit_is_still_judged(self):
        """The control for the control: narrowing the trigger must not make the
        hook blind to the thing it exists for."""
        self.assertEqual(
            decision('git commit -m "chore: x"', self.repo_on("develop")), "ask")
        self.assertEqual(
            decision('git commit -m "feat(X-1): y"', self.repo_on("feature/x")),
            "allow")


if __name__ == "__main__":
    unittest.main(verbosity=2)
