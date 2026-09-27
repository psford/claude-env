#!/usr/bin/env python3
"""The state-based git hooks, exercised by running real git.

These are not tested by feeding a command string to a parser, because not
parsing a command string is the entire point. Every case here runs actual git in
a scratch repository with core.hooksPath installed, and asserts on what ended up
in the repository rather than on what a guard said about it.

The forms below are the ones that defeated the PreToolUse text guard: eval,
sh -c, a script file, xargs, an inline alias, a line continuation. To this layer
they are indistinguishable from the plain form, which is the property being
tested.

Run: python3 .claude/hooks/tests/test_git_hooks.py
"""

import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HOOKS_DIR = os.path.join(REPO, "shared", "git-hooks")


def git(repo, *args, **kw):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, **kw)


def sh(repo, command, env=None):
    """Run a shell command in the repo, exactly as a person would."""
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(["bash", "-c", command], cwd=repo,
                          capture_output=True, text=True, env=e)


class HookCase(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.repo], check=False))
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "core.hooksPath", HOOKS_DIR)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        git(self.repo, "branch", "-M", "main")

    def count(self, ref="HEAD"):
        r = git(self.repo, "rev-list", "--count", ref)
        return int(r.stdout.strip() or 0)


class TestCommitOnProtectedBranch(HookCase):
    # AC1 — every one of these defeated the text guard.
    def assert_refused(self, command, label):
        before = self.count()
        sh(self.repo, command)
        self.assertEqual(self.count(), before, f"{label} produced a commit on main")

    def test_the_plain_form_is_refused(self):
        self.assert_refused('git commit -m x --allow-empty', "plain")

    def test_sh_c_is_refused(self):
        self.assert_refused("sh -c 'git commit -m x --allow-empty'", "sh -c")

    def test_eval_is_refused(self):
        self.assert_refused('eval "git commit -m x --allow-empty"', "eval")

    def test_a_script_file_is_refused(self):
        self.assert_refused(
            'printf "git commit -m x --allow-empty\\n" > s.sh; bash s.sh', "script file")

    def test_xargs_is_refused(self):
        self.assert_refused('echo "-m x --allow-empty" | xargs git commit', "xargs")

    def test_an_inline_alias_is_refused(self):
        self.assert_refused('git -c alias.ci=commit ci -m x --allow-empty', "inline alias")

    def test_a_line_continuation_is_refused(self):
        self.assert_refused('git \\\n  commit -m x --allow-empty', "line continuation")

    def test_a_variable_verb_is_refused(self):
        self.assert_refused('C=commit; git $C -m x --allow-empty', "variable verb")

    def test_the_refusal_says_what_to_do_instead(self):
        r = sh(self.repo, 'git commit -m x --allow-empty')
        self.assertIn("switch -c", r.stderr + r.stdout)


class TestItDoesNotBlockOrdinaryWork(HookCase):
    # AC2. A hook that blocks real work gets uninstalled, and an uninstalled
    # hook is worth less than no hook because it is believed to be running.
    def test_a_commit_on_a_feature_branch_is_allowed(self):
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        before = self.count()
        sh(self.repo, 'git commit -m x --allow-empty')
        self.assertEqual(self.count(), before + 1)

    def test_the_first_commit_in_a_fresh_repo_is_allowed(self):
        fresh = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", fresh], check=False))
        git(fresh, "init", "-q")
        git(fresh, "config", "user.email", "t@example.com")
        git(fresh, "config", "user.name", "t")
        git(fresh, "config", "core.hooksPath", HOOKS_DIR)
        # Default branch is main or master depending on git config -- exactly
        # the protected names. Refusing here makes new repos impossible.
        r = sh(fresh, 'git commit -m init --allow-empty')
        self.assertEqual(r.returncode, 0, f"bootstrapping a repo was blocked: {r.stderr}")

    def test_a_detached_head_is_not_treated_as_a_protected_branch(self):
        git(self.repo, "checkout", "-q", "--detach")
        r = sh(self.repo, 'git commit -m x --allow-empty')
        self.assertEqual(r.returncode, 0, "a detached HEAD was refused; rebase and bisect break")

    def test_an_explicit_override_with_a_reason_is_honoured(self):
        # Without an escape, the workaround becomes --no-verify, which disables
        # every hook rather than this one.
        before = self.count()
        r = sh(self.repo, 'git commit -m x --allow-empty',
               env={"ALLOW_PROTECTED_COMMIT": "importing an existing tree"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.count(), before + 1)


class TestPushToProtectedBranch(HookCase):
    # AC3
    def setUp(self):
        super().setUp()
        self.remote = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.remote], check=False))
        subprocess.run(["git", "init", "-q", "--bare", self.remote], check=True)
        git(self.repo, "remote", "add", "origin", self.remote)
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        sh(self.repo, 'git commit -m work --allow-empty')

    def remote_head(self):
        r = git(self.repo, "ls-remote", "origin", "refs/heads/main")
        return r.stdout.split()[0] if r.stdout.strip() else None

    def assert_remote_unchanged(self, command, label):
        before = self.remote_head()
        sh(self.repo, command)
        self.assertEqual(self.remote_head(), before, f"{label} changed main on the remote")

    def test_a_refspec_push_to_main_is_refused(self):
        self.assert_remote_unchanged('git push origin feature/x:main', "refspec")

    def test_a_head_refspec_push_is_refused(self):
        self.assert_remote_unchanged('git push origin HEAD:main', "HEAD refspec")

    def test_a_forced_refspec_push_is_refused(self):
        self.assert_remote_unchanged('git push origin +feature/x:main', "forced refspec")

    def test_deleting_main_is_refused(self):
        self.assert_remote_unchanged('git push origin :main', "delete via empty source")
        self.assert_remote_unchanged('git push origin --delete main', "delete via flag")

    def test_pushing_a_feature_branch_is_allowed(self):
        r = sh(self.repo, 'git push -q -u origin feature/x')
        self.assertEqual(r.returncode, 0, f"an ordinary push was refused: {r.stderr}")

    def test_the_refusal_explains_the_pull_request_route(self):
        r = sh(self.repo, 'git push origin HEAD:main')
        self.assertRegex((r.stderr + r.stdout), r"pull request|pr create")


class TestItChainsToTheRepositorysOwnHooks(HookCase):
    """core.hooksPath REPLACES the hook path rather than adding to it.

    Installing this without chaining would silently disable whatever a repo
    already had. Two workspace repos have their own hooks today, so this is not
    hypothetical -- and a silent loss of a repo's own checks is exactly the
    "no feature regression" rule.
    """

    def write_own(self, name, body):
        own_dir = os.path.join(self.repo, ".git", "hooks")
        os.makedirs(own_dir, exist_ok=True)
        path = os.path.join(own_dir, name)
        with open(path, "w") as fh:
            fh.write(body)
        os.chmod(path, 0o755)
        return path

    def test_the_repos_own_pre_commit_still_runs(self):
        marker = os.path.join(self.repo, "own-ran")
        self.write_own("pre-commit", f"#!/usr/bin/env bash\ntouch {marker}\nexit 0\n")
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        sh(self.repo, 'git commit -m x --allow-empty')
        self.assertTrue(os.path.exists(marker), "the repo's own pre-commit was silently dropped")

    def test_a_veto_from_the_repos_own_pre_commit_is_respected(self):
        self.write_own("pre-commit", "#!/usr/bin/env bash\necho own-hook-says-no >&2\nexit 1\n")
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        before = self.count()
        r = sh(self.repo, 'git commit -m x --allow-empty')
        self.assertEqual(self.count(), before, "the repo's own veto was ignored")
        self.assertIn("own-hook-says-no", r.stderr)

    def test_the_repos_own_pre_push_still_receives_the_ref_list(self):
        # stdin can only be read once, so the ref list has to be captured and
        # replayed. A chained hook that receives an empty stdin is worse than
        # one that is not called: it silently approves everything.
        out = os.path.join(self.repo, "own-refs")
        self.write_own("pre-push", f"#!/usr/bin/env bash\ncat > {out}\nexit 0\n")
        remote = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", remote], check=False))
        subprocess.run(["git", "init", "-q", "--bare", remote], check=True)
        git(self.repo, "remote", "add", "origin", remote)
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        sh(self.repo, 'git commit -m work --allow-empty')
        sh(self.repo, 'git push -q -u origin feature/x')
        self.assertTrue(os.path.exists(out), "the repo's own pre-push was not called")
        with open(out) as fh:
            body = fh.read()
        self.assertIn("refs/heads/feature/x", body,
                      "the chained pre-push got an empty ref list, so it approved blindly")


class TestKnownLimitsAreRealAndStated(HookCase):
    """These are not failures. They are the reason branch protection exists.

    Asserting them keeps the corpus honest: if --no-verify ever stopped working
    as an escape, the corpus entry claiming `server` would be stale and this
    would say so.
    """

    def test_no_verify_skips_the_hook(self):
        before = self.count()
        sh(self.repo, 'git commit --no-verify -m x --allow-empty')
        self.assertEqual(self.count(), before + 1,
                         "--no-verify no longer skips hooks; the corpus record is stale")

    def test_plumbing_does_not_run_hooks(self):
        r = sh(self.repo, 'T=$(git write-tree); git commit-tree $T -m x')
        self.assertEqual(r.returncode, 0,
                         "commit-tree now runs hooks; the corpus record is stale")


# A stand-in for `dotnet`, first on PATH. The hook calls it as
# `dotnet test <tmp>/runner/HarnessRunner.sln ...`; it logs the call, then passes
# or fails on the `verdict` file beside that solution -- a file in the tree the
# hook EXPORTED, so the verdict says which tree was judged.
STUB_DOTNET = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
verdict=$(cat "$(dirname "$2")/verdict")
if [ "$verdict" = pass ]; then
  exit 0
fi
echo "stub suite: $verdict"
exit 1
"""


class TestTheRunnerGate(HookCase):
    """CE-2.95 (Patrick's yes on CH-189): a commit that stages anything under
    runner/ runs the runner's tests against the staged tree, and is refused
    unless they pass. Every case uses a stub dotnet; none needs the real SDK."""

    def setUp(self):
        super().setUp()
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.stub_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", self.stub_dir], check=False))
        stub = os.path.join(self.stub_dir, "dotnet")
        with open(stub, "w") as fh:
            fh.write(STUB_DOTNET)
        os.chmod(stub, 0o755)
        self.stub_log = os.path.join(self.stub_dir, "calls.log")
        self.env = {"PATH": self.stub_dir + os.pathsep + os.environ["PATH"],
                    "STUB_LOG": self.stub_log}

    def write(self, rel, body):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(body)

    def stage_runner(self, verdict):
        self.write("runner/HarnessRunner.sln", "solution\n")
        self.write("runner/verdict", verdict)
        git(self.repo, "add", "runner")

    def commit(self, env=None):
        return sh(self.repo, 'git commit -q -m work', env=env or self.env)

    def dotnet_ran(self):
        return os.path.exists(self.stub_log)

    def test_a_failing_runner_suite_refuses_the_commit(self):
        self.stage_runner("fail")
        before = self.count()
        r = self.commit()
        self.assertEqual(self.count(), before, "a failing runner suite was committed")
        self.assertIn("runner", r.stderr)

    def test_a_passing_runner_suite_allows_the_commit(self):
        self.stage_runner("pass")
        before = self.count()
        r = self.commit()
        self.assertEqual(self.count(), before + 1, r.stderr)
        self.assertTrue(self.dotnet_ran(), "the gate never ran the suite")

    def test_no_dotnet_refuses_a_runner_commit(self):
        # A PATH holding every program the system has except dotnet (and not
        # the stub). /bin is /usr/bin here, so both are covered by one copy.
        bare = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", bare], check=False))
        for name in os.listdir("/usr/bin"):
            if name != "dotnet":
                os.symlink(os.path.join("/usr/bin", name), os.path.join(bare, name))
        self.stage_runner("pass")
        before = self.count()
        r = self.commit(env={"PATH": bare, "STUB_LOG": self.stub_log})
        self.assertEqual(self.count(), before, "a runner commit went through with no dotnet")
        self.assertIn("dotnet", r.stderr)

    def test_a_commit_outside_runner_never_runs_dotnet(self):
        self.write("notes.txt", "notes\n")
        git(self.repo, "add", "notes.txt")
        before = self.count()
        self.commit()
        self.assertEqual(self.count(), before + 1)
        self.assertFalse(self.dotnet_ran(), "dotnet ran for a commit that touches no runner/")

    def test_the_gate_judges_the_staged_tree(self):
        # Staged pass, working tree fail: the commit ships the index, so it goes.
        self.stage_runner("pass")
        self.write("runner/verdict", "fail")
        before = self.count()
        r = self.commit()
        self.assertEqual(self.count(), before + 1,
                         f"the gate judged the working tree, not the index: {r.stderr}")
        # Staged fail, working tree pass: refused.
        self.write("runner/verdict", "fail")
        git(self.repo, "add", "runner/verdict")
        self.write("runner/verdict", "pass")
        before = self.count()
        self.commit()
        self.assertEqual(self.count(), before,
                         "a staged failing suite was committed because the working tree passed")

    def test_the_trigger_is_anchored_at_runner(self):
        self.stage_runner("pass")
        self.write("runner/extra.txt", "x\n")
        git(self.repo, "add", "runner/extra.txt")
        self.commit()
        # A rename out of runner/ runs the gate.
        os.remove(self.stub_log)
        git(self.repo, "mv", "runner/extra.txt", "moved.txt")
        self.commit()
        self.assertTrue(self.dotnet_ran(), "a rename out of runner/ skipped the gate")
        # A deletion under runner/ runs the gate.
        os.remove(self.stub_log)
        self.write("runner/gone.txt", "x\n")
        git(self.repo, "add", "runner/gone.txt")
        self.commit()
        os.remove(self.stub_log)
        git(self.repo, "rm", "-q", "runner/gone.txt")
        self.commit()
        self.assertTrue(self.dotnet_ran(), "a deletion under runner/ skipped the gate")
        # A path that only starts with "runner" does not.
        os.remove(self.stub_log)
        self.write("runner-notes.md", "notes\n")
        git(self.repo, "add", "runner-notes.md")
        self.commit()
        self.assertFalse(self.dotnet_ran(), "runner-notes.md triggered the runner gate")

    def test_a_detached_head_runner_commit_is_still_gated(self):
        git(self.repo, "checkout", "-q", "--detach")
        self.stage_runner("fail")
        before = self.count()
        self.commit()
        self.assertEqual(self.count(), before,
                         "a failing runner suite was committed on a detached HEAD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
