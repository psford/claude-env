#!/usr/bin/env python3
"""What shared_rules_link_guard SAYS when it refuses a commit in a NESTED
agent worktree (CE-2.37).

Why this file exists rather than another fixture: the guard's refusal, at
HEAD, tells every reader to repair a broken shared-rules link by running
`sync-claude-md.sh` on the repo root -- correct advice for an ordinary
checkout, and actively harmful advice inside an agent worktree nested under
`<repo>/.claude/worktrees/`.

A worktree there is its own checkout with its own (deeper) path to
`.claude/rules/`. Running sync-claude-md.sh from inside it computes new
relative symlink targets that are correct for THAT depth. If those targets
are ever committed -- and `.claude/rules/*.md` is tracked in at least one
companion repo -- every ORDINARY checkout inherits a link that resolves to
nothing, because it is not nested six levels deep. A dev followed the
guard's own advice and did exactly this (claude-harness acb56dd).

The fix is not to repair the links in place; it is to stop working inside
the nested worktree. `git worktree move` relocates it to a directory beside
claude-env, where the ordinary (shallow) relative links are correct again.
So the nested-worktree refusal must name that move and must NOT repeat the
sync-claude-md.sh advice -- including the remedy line sync-claude-md.sh's
own --check prints ("run helpers/sync-claude-md.sh <repo>"), which the guard
forwards verbatim and which is exactly the advice that must not appear here.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "shared_rules_link_guard.py")

CLAUDE_MD_JSON = json.dumps({"fragments": ["00-universal"], "vars": {}})


def _git(args, cwd):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True,
                    capture_output=True, text=True)


def _write_claude_md_json(repo):
    d = os.path.join(repo, ".claude")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "claude-md.json"), "w") as fh:
        fh.write(CLAUDE_MD_JSON)


class TestTheRefusalInANestedWorktree(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", self.base], check=False))

    def refuse(self, cwd):
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "git commit -m wip"},
                              "cwd": cwd})
        p = subprocess.run([sys.executable, HOOK], input=payload,
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 2, p.stderr)
        return p.stderr

    def test_it_names_moving_the_worktree_not_the_sync(self):
        # An ordinary checkout: a plain repo with a broken/missing shared-
        # rules link. Its refusal must still name sync-claude-md.sh, exactly
        # as today.
        ordinary = os.path.join(self.base, "ordinary-repo")
        os.makedirs(ordinary)
        _git(["init", "-q", ordinary], self.base)
        _write_claude_md_json(ordinary)

        ordinary_err = self.refuse(ordinary)
        self.assertIn("sync-claude-md.sh", ordinary_err)

        # An agent worktree nested under <repo>/.claude/worktrees/. Its
        # refusal must name `git worktree move` beside claude-env instead,
        # and must not tell the reader to run sync-claude-md.sh on it --
        # that rewrites the tracked links so they dangle in every normal
        # checkout (claude-harness acb56dd).
        main_repo = os.path.join(self.base, "main-repo")
        os.makedirs(main_repo)
        _git(["init", "-q", "-b", "main", main_repo], self.base)
        _git(["config", "user.email", "test@example.com"], main_repo)
        _git(["config", "user.name", "Test"], main_repo)
        _write_claude_md_json(main_repo)
        _git(["add", "."], main_repo)
        _git(["commit", "-q", "-m", "initial"], main_repo)

        worktrees_dir = os.path.join(main_repo, ".claude", "worktrees")
        os.makedirs(worktrees_dir, exist_ok=True)
        nested = os.path.join(worktrees_dir, "agent-x")
        _git(["worktree", "add", "-q", "-b", "agent-x-branch", nested, "main"],
             main_repo)

        nested_err = self.refuse(nested)
        self.assertIn("git worktree move", nested_err)
        self.assertNotIn("sync-claude-md.sh", nested_err)


if __name__ == "__main__":
    unittest.main()
