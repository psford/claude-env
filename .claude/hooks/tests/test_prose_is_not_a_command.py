#!/usr/bin/env python3
"""One test for the whole class: a heredoc body is data, and no hook may judge it.

This defect has been found and fixed one hook at a time for two days --
main_branch_guard blocking its own commit over a quoted `--force`, the ticket
guards reading a commit message as an invocation, and on 2026-08-09
commit_claim_verify_guard and prod_target_verify_guard firing on the text of the
fixture files being written to test them. Patrick, reasonably: *"you really need
to fix this heredoc issue once and for all."*

Fixing the offenders is not that. THIS is: a behavioural check across every hook
that reads tool_input.command, so a new hook cannot reintroduce the bug quietly.

Behavioural on purpose. The obvious version greps each hook for
strip_heredoc_bodies, and a grep audit is the instrument this repo has already
been burned by -- one searched for `rev-parse --abbrev-ref`, a string that could
never appear because the arguments are a Python list, and returned clean over 31
broken hooks. This one hands each hook a real payload and reads what it does.

The corpus is deliberately inflammatory: the heredoc body contains a forced
push, a commit on main, a reset --hard, a production connection string, a
deploy, and several verification claims. Every one of those is something some
hook in this directory exists to catch. None of them is a command here -- they
are lines in a document being written to disk.

Run: python3 .claude/hooks/tests/test_prose_is_not_a_command.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A document that talks about dangerous things, written with a heredoc.
# The command line itself (`cat > notes.md <<'EOF'`) is a real command and is
# deliberately still scannable -- a redirect written there is a redirect.
PROSE_PAYLOAD = """cat > docs/notes.md <<'EOF'
# What went wrong

We ran `git push --force origin main` and lost a day. Do not do that.

The fix was NOT `git reset --hard HEAD~1`, which destroyed uncommitted work
once already.

Never run: git commit -m "hotfix" directly on main.

The connection string was WSL_SQL_CONNECTION="Server=tcp:prod.database.windows.net;"
and dotnet run picked up the wrong database.

We deploy with `npm run cf:deploy` only after tests pass and it is verified,
confirmed working, and visible in production.

rm -rf node_modules was suggested and rejected.
EOF"""


def hooks_that_read_a_command():
    """Every hook that inspects tool_input.command, found by reading the source.

    The list is derived rather than hand-maintained: a hand list is a list that
    goes stale the first time someone adds a hook.
    """
    found = []
    for name in sorted(os.listdir(HOOKS)):
        if not name.endswith(".py") or name.startswith("_"):
            continue
        path = os.path.join(HOOKS, name)
        try:
            src = open(path).read()
        except OSError:
            continue
        if "tool_input" in src and '"command"' in src:
            found.append((name[:-3], path))
    return found


class TestProseIsNotACommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = hooks_that_read_a_command()
        cls.repo = tempfile.mkdtemp()
        run = lambda *a: subprocess.run(a, cwd=cls.repo, capture_output=True)  # noqa: E731
        subprocess.run(["git", "init", "-q", "-b", "feature/notes", cls.repo], check=True)
        run("git", "config", "user.email", "t@example.com")
        run("git", "config", "user.name", "t")
        os.makedirs(os.path.join(cls.repo, "docs"), exist_ok=True)
        open(os.path.join(cls.repo, "README.md"), "w").write("baseline\n")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "baseline")

    def test_the_instrument_finds_hooks_at_all(self):
        """A clean result from an empty list means nothing."""
        self.assertGreater(len(self.hooks), 20,
                           "expected to find many command-scanning hooks")

    def test_no_hook_judges_a_heredoc_body(self):
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": PROSE_PAYLOAD},
            "cwd": self.repo,
        })

        offenders = []
        for name, path in self.hooks:
            done = subprocess.run([sys.executable, path], input=payload,
                                  capture_output=True, text=True, cwd=self.repo,
                                  timeout=30)
            spoke = ""
            if done.returncode != 0:
                spoke = f"exit {done.returncode}: {(done.stderr or '').strip()[:160]}"
            else:
                out = (done.stdout or "").strip()
                if out:
                    try:
                        ctx = (json.loads(out).get("hookSpecificOutput") or {}) \
                            .get("additionalContext") or ""
                    except Exception:
                        ctx = out
                    if ctx.strip():
                        spoke = f"spoke: {ctx.strip()[:160]}"
            if spoke:
                offenders.append(f"{name} — {spoke}")

        self.assertEqual(offenders, [], "\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=2)
