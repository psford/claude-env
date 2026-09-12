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
    """The hook's `hookSpecificOutput`, or None when it said NOTHING.

    CH-237.7. This used to answer `{"permissionDecision": "allow"}` when the
    hook printed nothing at all -- fabricating a grant the hook never issued.
    That is the same conflation F3 is about: an ACTIVE grant, which suppresses
    the permission prompt, reading identically to abstaining. A helper that
    cannot tell them apart cannot test a bug made of exactly that difference,
    and `test_a_feature_branch_is_not_interrupted_at_all` passed either way.

    Silence is None. Every caller now has to say which one it means.
    """
    p = subprocess.run(
        [sys.executable, GUARD],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}, "cwd": cwd}),
        capture_output=True, text=True, cwd=cwd)
    if not p.stdout.strip():
        return None
    return json.loads(p.stdout)["hookSpecificOutput"]


def decision(command, cwd):
    """Just the verdict, with silence as None. One subprocess call site, so
    the two helpers cannot drift into disagreeing about what the hook said."""
    out = run(command, cwd)
    # None for silence AND for an advisory result that carries no decision --
    # CH-237.6 made this hook advisory, so "said something" and "decided
    # something" are now different questions.
    return None if out is None else out.get("permissionDecision")


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
        self.assertIsNotNone(out, "the reminder is gone entirely")
        # CH-237.6 answer A: this hook is advisory now. It must NOT decide --
        # gate_git_commit is the sole decider -- but the reminder is the whole
        # reason the file still exists, so it has to survive.
        self.assertNotIn("permissionDecision", out,
                         "the advisory hook is deciding again")
        ctx = out.get("additionalContext", "")
        self.assertIn("ON THE BOARD", ctx)
        self.assertIn("ticket ask", ctx)
        self.assertIn("--audience patrick", ctx)

    def test_a_feature_branch_is_not_interrupted_at_all(self):
        """The control. Without it, "remind on everything" passes this file and
        the per-commit bottleneck the exemption exists to remove comes back."""
        out = run('git commit -m "feat(X-1): y"', self.repo_on("feature/x"))
        # CH-237.6 answer A. This used to be an active grant -- an "allow" that
        # suppressed the prompt for a command this hook could not verify the
        # protocol on. It is silence now: nothing to remind about off develop,
        # and nothing to decide. The distinction is the whole of F3, and it is
        # only assertable because `run()` stopped reporting silence as allow.
        self.assertIsNone(out, "the hook is still issuing a grant")


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

    # Both tests below assert SILENCE -- that the hook emitted nothing at all
    # -- and not merely that it issued no permissionDecision.
    #
    # QA bounce, 2026-09-11: they used to ask `decision(...) is None`, and
    # CH-237.6 had just made this hook advisory, so it no longer emits a
    # permissionDecision for ANY input. The assertion could not fail. Reverting
    # the narrowed trigger to the old broad regex left all six tests green
    # while the hook leaked its reminder onto `git log --grep commit` again --
    # the precise false positive the story exists to kill.
    #
    # A test that cannot fail is worse than no test: it reports the property is
    # held. Silence is the real contract, so it is what gets asserted.

    def test_a_command_that_only_names_the_words_draws_no_decision(self):
        # On a FEATURE branch, because that is where the old regex granted
        # rather than merely prompted -- the more dangerous half.
        feature = self.repo_on("feature/x")
        for command in self.NOT_COMMITS:
            with self.subTest(command=command):
                self.assertIsNone(
                    run(command, feature),
                    f"the hook spoke about {command!r}, which is not a commit")
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
                    run(command, develop),
                    f"the hook spoke about {command!r} on develop; the "
                    f"reminder belongs on commits, not on every mention of one")
                self.assertIsNone(
                    decision(command, develop),
                    f"the hook issued a decision for {command!r} on develop; a "
                    f"dispatched agent cannot answer an ask")

    def test_a_real_commit_is_still_seen(self):
        """The control for the control: narrowing the trigger must not make the
        hook blind to the thing it exists for.

        CH-237.6 answer A changed what "seen" means. This hook no longer judges
        anything -- gate_git_commit is the sole decider -- so the assertion is
        that a real commit on develop still draws the CE-2.4 reminder, which is
        the only capability this file has that gate_git_commit lacks.
        """
        out = run('git commit -m "chore: x"', self.repo_on("develop"))
        self.assertIsNotNone(out, "a real commit drew nothing at all")
        self.assertIn("ON THE BOARD", out.get("additionalContext", ""))
        self.assertIsNone(out.get("permissionDecision"),
                          "the advisory hook is judging again")

    def test_exactly_one_hook_decides_a_commit_payload(self):
        """AC4, the question Patrick answered A to.

        Two hooks used to return a permissionDecision for the same commit, and
        on a feature branch they disagreed -- git_commit_guard said allow,
        gate_git_commit said ask -- with precedence decided by read order and
        recorded nowhere. Asserted on a FEATURE branch because that is where
        they contradicted each other.
        """
        gate = os.path.join(HOOKS, "gate_git_commit.py")
        if not os.path.exists(gate):
            self.skipTest("gate_git_commit.py is not present in this checkout")
        repo = self.repo_on("feature/x")
        command = 'git commit -m "feat(X-1): y"'
        deciders = []
        for hook in (GUARD, gate):
            p = subprocess.run(
                [sys.executable, hook],
                input=json.dumps({"tool_name": "Bash", "cwd": repo,
                                  "tool_input": {"command": command}}),
                capture_output=True, text=True, cwd=repo)
            if not p.stdout.strip():
                continue
            try:
                block = json.loads(p.stdout)["hookSpecificOutput"]
            except Exception:
                continue
            if block.get("permissionDecision"):
                deciders.append(os.path.basename(hook))
        self.assertLessEqual(len(deciders), 1,
                             f"more than one hook decided this commit: {deciders}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
