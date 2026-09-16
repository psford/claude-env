#!/usr/bin/env python3
"""hatch_authoring_guard refuses the commit its own message asks for (CE-12.10).

CE-12.4 taught the guard to refuse a commit that stages hatch_inventory.json
alongside a file under .claude/hooks/, because the record cannot police a
change it is part of -- and to tell the author "Commit them separately" so
the inventory change can land on its own. `_staged_hook_files` (line 102)
matches every staged path under `.claude/hooks/` by prefix, and the inventory
lives at exactly that prefix, so it counts itself as a hook file. The result:
a commit staging ONLY the inventory trips the same "both at once" check
against itself and is refused -- the exact commit the refusal message tells
the author to make.

Modelled on tests/test_clyde_dispatch_review_guard.py: a subprocess run of
the live hook against a real payload, not a mock of its internals. This one
needs a real git repository, since the guard's decision depends on what is
actually staged there.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "hatch_authoring_guard.py")


def _run_guard(repo):
    """The guard's result for `git commit -m x` staged as `repo` currently is."""
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m x"},
        "cwd": repo,
    })
    return subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, check=False)


def _stage(repo, relative_path, content):
    full = os.path.join(repo, relative_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    subprocess.run(["git", "add", relative_path], cwd=repo, check=True)


class TestTheInventoryCommitsOnItsOwn(unittest.TestCase):
    def test_an_inventory_only_commit_is_allowed_and_a_mixed_commit_is_still_refused(self):
        repo = tempfile.mkdtemp(prefix="hatch-authoring-guard-test-")
        try:
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

            # Case one: the inventory, and only the inventory, is staged.
            # This is precisely the commit the guard's own refusal tells an
            # author to make when a mixed commit is rejected, so it must be
            # allowed.
            _stage(repo, ".claude/hooks/hatch_inventory.json", "{}\n")
            inventory_only = _run_guard(repo)
            self.assertEqual(
                0, inventory_only.returncode,
                f"an inventory-only commit was refused: "
                f"{inventory_only.stderr!r}")

            # Case two, the control: a real hook file staged alongside the
            # inventory must still be refused -- the guard's actual job,
            # unchanged.
            _stage(repo, ".claude/hooks/some_new_guard.py",
                  "# not a real hook, just a staged file\n")
            mixed = _run_guard(repo)
            self.assertEqual(
                2, mixed.returncode,
                "a commit staging a hook file together with the inventory "
                "was not refused")
            self.assertIn("Commit them separately", mixed.stderr)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
