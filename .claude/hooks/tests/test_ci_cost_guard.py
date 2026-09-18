#!/usr/bin/env python3
"""ci_cost_guard: the dormancy gap -- leaving the repo was not an off switch.

CE-25.8 / CE-25 4.6. `_judge` used to `return 0` when the target directory
was not a git repo at all, so a dispatch or push judged from outside any
checkout skipped every check this guard exists to run -- including the
permanent iOS-on-GitHub ban. Measured in the epic's lab (CE-25 1.2, E2/E3):
`cd /tmp && gh workflow run ios.yml` and a plain cwd=/tmp dispatch both
returned rc=0 at 212dd3e.

The fix folds that case into the rule the -R path already states: a repo
this guard cannot inspect is not a repo it may approve. This file is the
python-level test that exercises it directly, because the fixture suite
(.claude/hooks/tests/ci_cost_guard/*.md) always stages a scratch git repo
before every fixture (run-hook-tests.sh inits one up front) -- it cannot ask
"what if there is no repo at all," and TestDormancy is what answers that.

Run: python3 .claude/hooks/tests/test_ci_cost_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GUARD = os.path.join(HOOKS, "ci_cost_guard.py")

# The payload strings below are never executed -- the guard only reads them
# as text from the JSON on stdin, exactly as the existing fixture COMMAND=
# lines do. Named as constants so no gated phrase needs retyping per call.
DISPATCH_CMD = "gh workflow run ios.yml"
PUSH_CMD = "git push origin main"


def run(command, cwd, env_overrides=None):
    """The guard's raw exit code (and stderr) for one command judged from cwd.

    CI_RUN_OK / CI_MACOS_PUSH_OK are stripped from the inherited environment
    first so a stray export in the launching shell cannot leak an ack into a
    case that is supposed to be un-acked.
    """
    full_env = dict(os.environ)
    full_env.pop("CI_RUN_OK", None)
    full_env.pop("CI_MACOS_PUSH_OK", None)
    if env_overrides:
        full_env.update(env_overrides)
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}, "cwd": cwd})
    p = subprocess.run([sys.executable, GUARD], input=payload,
                        capture_output=True, text=True, cwd=cwd, env=full_env)
    return p.returncode, p.stderr


class GuardCase(unittest.TestCase):
    def make_repo(self, macos):
        """A scratch git repo with one workflow file, macOS or Linux runner."""
        path = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", path], check=False))
        subprocess.run(["git", "init", "-q", "-b", "main", path], check=True)
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            subprocess.run(["git", "config", k, v], cwd=path, check=True)
        wf_dir = os.path.join(path, ".github", "workflows")
        os.makedirs(wf_dir)
        runner = "macos-14" if macos else "ubuntu-latest"
        name = "ios.yml" if macos else "ci.yml"
        with open(os.path.join(wf_dir, name), "w") as fh:
            fh.write(f"on: push\njobs:\n  build:\n    runs-on: {runner}\n")
        subprocess.run(["git", "add", "-A"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "wf"], cwd=path, check=True)
        return path

    def make_non_repo(self):
        path = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", "--", path], check=False))
        return path


class TestDormancy(GuardCase):
    def test_a_dispatch_from_a_non_repo_cwd_is_refused(self):
        """AC1. E2/E3 from CE-25 1.2: leaving the repo used to be the off
        switch for the whole dispatch gate, including the permanent iOS ban.
        Both the `cd`-out-of-a-repo shape (E2) and a plain non-repo cwd (E3)
        must now refuse, and the same is true of a push judged the same way."""
        non_repo = self.make_non_repo()
        session_repo = self.make_repo(macos=False)

        # E2: the session sits in a real repo, but the command cd's out of
        # it before dispatching -- the repo the command actually names is
        # the non-repo directory, not the session's.
        rc, _ = run(f"cd {non_repo} && {DISPATCH_CMD}", cwd=session_repo)
        self.assertEqual(rc, 2, "a dispatch that cd's out of the repo first was not refused")

        # E3: cwd itself is not a git repo at all, no cd involved.
        rc, _ = run(DISPATCH_CMD, cwd=non_repo)
        self.assertEqual(rc, 2, "a dispatch judged from a plain non-repo cwd was not refused")

        # The same dormancy gap applied to the push path.
        rc, _ = run(PUSH_CMD, cwd=non_repo)
        self.assertEqual(rc, 2, "a push judged from a non-repo cwd was not refused")


class TestInRepoBehaviourIsUnchanged(GuardCase):
    def test_in_repo_behaviour_and_ack_paths_are_unchanged(self):
        """AC2. The fix touches only the repo_root-is-None path. Everything
        that already worked inside a real checkout -- the permanent macOS
        dispatch ban (no bypass exists), the CI_RUN_OK ack gate, macOS
        push-reachability, and CI_MACOS_PUSH_OK -- must decide exactly as it
        did at the parent commit (same shapes the existing fixtures 01-06
        assert, run here at the python level so the dormancy fix is proven
        not to have moved them)."""
        macos_repo = self.make_repo(macos=True)
        linux_repo = self.make_repo(macos=False)

        # 01: permanent iOS ban, unconditional -- no ack can lift it.
        rc, _ = run(DISPATCH_CMD, cwd=macos_repo)
        self.assertEqual(rc, 2, "the permanent iOS dispatch ban regressed")
        rc, _ = run(DISPATCH_CMD, cwd=macos_repo, env_overrides={"CI_RUN_OK": "1"})
        self.assertEqual(rc, 2, "CI_RUN_OK must not lift the permanent iOS ban")

        # 02/03: an ordinary Linux dispatch needs the CI_RUN_OK ack.
        rc, _ = run(DISPATCH_CMD, cwd=linux_repo)
        self.assertEqual(rc, 2, "an un-acked Linux dispatch was allowed")
        rc, _ = run(DISPATCH_CMD, cwd=linux_repo, env_overrides={"CI_RUN_OK": "1"})
        self.assertEqual(rc, 0, "the CI_RUN_OK ack path regressed")

        # 04/05: a push reachable to a macOS job needs CI_MACOS_PUSH_OK.
        rc, _ = run(PUSH_CMD, cwd=macos_repo)
        self.assertEqual(rc, 2, "a push reachable to a macOS job was allowed")
        rc, _ = run(PUSH_CMD, cwd=macos_repo, env_overrides={"CI_MACOS_PUSH_OK": "1"})
        self.assertEqual(rc, 0, "the CI_MACOS_PUSH_OK ack path regressed")

        # 06: a plain Linux-only push stays zero-friction.
        rc, _ = run(PUSH_CMD, cwd=linux_repo)
        self.assertEqual(rc, 0, "a plain Linux-only push was blocked")

        # The -R/--repo path (CH-237.10, fixture 28): a named repo no
        # checkout on this machine resolves to must still refuse exactly as
        # before -- this is the rule the dormancy fix now shares.
        rc, stderr = run(f"gh workflow run -R acme/does-not-exist-anywhere build.yml",
                          cwd=linux_repo, env_overrides={"CI_RUN_OK": "1"})
        self.assertEqual(rc, 2, "an unresolvable -R/--repo target was allowed")
        self.assertIn("-R/--repo", stderr, "the named-repo refusal message changed")


if __name__ == "__main__":
    unittest.main()
