#!/usr/bin/env python3
"""Tests for the structural hatch scan, and for what the guard does with it.

CE-12.4, and the QA bounce that asked for this file. The work shipped with
every criterion pinned by a scratch probe under /tmp, which is to say pinned
by nothing: the mechanism this ticket exists to protect had no regression
test at all, in an epic about controls that regressed silently.

The fixture suite (run-hook-tests.sh) asserts a hook's exit code against one
COMMAND string. That cannot express any of the questions here -- every one of
them is about what is STAGED in a repository when the commit is judged -- so
this is a unit test alongside it, the same arrangement test_repo_context.py
already uses for the same reason.

Two layers, deliberately:

  waivers()   the shape question alone, with no git and no subprocess, so a
              failure says which half broke.
  the guard   the whole refusal, driven exactly as Claude Code drives it: a
              PreToolUse payload on stdin, in a real repository with real
              staged files.

Run: python3 .claude/hooks/tests/test_hatch_shape_scan.py
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HOOKS)
from hatch_shape_scan import waivers  # noqa: E402

GUARD = os.path.join(HOOKS, "hatch_authoring_guard.py")
ROOT = os.path.abspath(os.path.join(HOOKS, "..", ".."))

# Built at import time rather than written out, so this file is not itself a
# token the scan finds when the guard reads the staged hooks directory.
SNEAK = "SNEAKY" + "_OK"


class TestTheShapeOfAWaiver(unittest.TestCase):
    """`in` abandons the check. `not in` decides the guard does not apply.

    That asymmetry is the entire discriminator, and it is why this scan needs
    no list of token spellings. Measured across the 51 hooks when it was
    written: nine of the second, one of the first.
    """

    def test_a_literal_in_the_command_that_returns_is_a_waiver(self):
        src = ('def main(command):\n'
               '    if "--just-let-me" in command:\n'
               '        return 0\n'
               '    return 2\n')
        self.assertEqual(waivers(src), [(2, "--just-let-me")])

    def test_the_negation_is_a_trigger_and_is_left_alone(self):
        """The allow direction, and the expensive one to get wrong.

        Nine ordinary guards ask `if <thing> not in command: return 0` to
        establish that they do not apply. Treating that as a waiver would
        make every one of them uncommittable.
        """
        src = ('def main(command):\n'
               '    if "git commit" not in command:\n'
               '        return 0\n'
               '    return 2\n')
        self.assertEqual(waivers(src), [])

    def test_a_constant_is_resolved_to_the_string_it_holds(self):
        """The CWD_DRIFT_OK shape exactly: underscores, no colon, indirect.

        The spelling scan looked for `NAME-OK` followed by a colon, so the
        one mechanism the epic is named after was the one it could not see.
        """
        src = (f'ESCAPE = "{SNEAK}"\n'
               'def main(command):\n'
               '    if ESCAPE in command:\n'
               '        return 0\n')
        self.assertEqual(waivers(src), [(3, SNEAK)])

    def test_every_name_a_hook_gives_its_command_text_is_watched(self):
        for name in ("command", "cmd", "text", "message", "body"):
            with self.subTest(name=name):
                src = (f'def main({name}):\n'
                       f'    if "TOK" in {name}:\n'
                       '        return 0\n')
                self.assertEqual(waivers(src), [(2, "TOK")])

    def test_a_branch_that_does_work_is_not_a_waiver(self):
        """Abandoning the check is the act. Doing something is not."""
        src = ('def main(command):\n'
               '    if "sudo" in command:\n'
               '        warn()\n'
               '    return 2\n')
        self.assertEqual(waivers(src), [])

    def test_returning_a_refusal_is_not_a_waiver(self):
        """`return 2` on a match is a guard firing, the opposite of a hatch."""
        src = ('def main(command):\n'
               '    if "rm -rf /" in command:\n'
               '        return 2\n'
               '    return 0\n')
        self.assertEqual(waivers(src), [])

    def test_reading_the_environment_is_not_a_waiver(self):
        """Deliberately allowed, and the reason is in the guard's docstring.

        A `VAR=1 <cmd>` prefix sets the environment of the command bash runs,
        not of the hook that judged it, so only the shell that LAUNCHES the
        session can set one. That is the shape the shared rules permit.
        """
        src = ('import os\n'
               'def main(command):\n'
               '    if os.environ.get("CI_RUN_OK") == "1":\n'
               '        return 0\n')
        self.assertEqual(waivers(src), [])

    def test_a_file_that_does_not_parse_yields_nothing_not_a_crash(self):
        self.assertEqual(waivers("def main(:\n"), [])


def _repo():
    """A git repo whose hooks directory is already committed.

    The scaffolding is committed first so a later `git add -A` stages ONLY
    the file under test. Without that step every case staged the inventory
    too and the same-commit check fired on all of them -- a property of the
    fixture, not of the guard.
    """
    path = tempfile.mkdtemp(prefix="ce124_")
    hooks = os.path.join(path, ".claude", "hooks")
    os.makedirs(hooks)
    for name in ("hatch_inventory.json", "_repo_context.py",
                 "hatch_shape_scan.py"):
        shutil.copy(os.path.join(HOOKS, name), os.path.join(hooks, name))
    subprocess.run(["git", "init", "-q", path], check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "config", key, value], cwd=path,
                       check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "scaffolding"], cwd=path,
                   check=True)
    return path


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.repo = _repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

    def judge(self, name, body, touch_inventory=False):
        """Stage `body` as a hook and ask the guard about a commit."""
        hooks = os.path.join(self.repo, ".claude", "hooks")
        with open(os.path.join(hooks, name), "w") as handle:
            handle.write(body)
        if touch_inventory:
            inventory = os.path.join(hooks, "hatch_inventory.json")
            with open(inventory, "a") as handle:
                handle.write("\n")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        payload = json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "git commit -m x"},
                              "cwd": self.repo})
        done = subprocess.run([sys.executable, GUARD], input=payload,
                              text=True, capture_output=True, cwd=self.repo)
        return done.returncode, done.stderr


class TestTheGuardRefuses(GuardCase):

    def test_a_waiver_reached_through_a_constant(self):
        """AC2. Underscores, no colon -- invisible to the spelling scan."""
        code, err = self.judge("sneak_guard.py",
                               f'ESCAPE = "{SNEAK}"\n'
                               'def main(command):\n'
                               '    if ESCAPE in command:\n'
                               '        return 0\n')
        self.assertEqual(code, 2)
        self.assertIn(SNEAK, err)

    def test_a_hyphenated_flag_with_no_colon(self):
        """AC3. `--ignore-engines` was live and unseen for exactly this."""
        code, err = self.judge("flag_guard.py",
                               'def main(command):\n'
                               '    if "--just-let-me" in command:\n'
                               '        return 0\n')
        self.assertEqual(code, 2)
        self.assertIn("--just-let-me", err)

    def test_a_token_in_a_hook_that_is_not_python(self):
        """AC3. A hatch in a shell hook was invisible for no reason other
        than its extension."""
        shelly = "SHELLY" + "-OK"
        code, err = self.judge(
            "sh_guard.sh",
            '#!/usr/bin/env bash\n'
            f'if [[ "$COMMAND" == *"{shelly}:"* ]]; then exit 0; fi\n')
        self.assertEqual(code, 2)
        self.assertIn(shelly, err)

    def test_the_inventory_and_a_hook_in_one_commit(self):
        """AC1. The record cannot police a change it is part of."""
        code, err = self.judge("plain_guard.py",
                               'import re\n'
                               'R = re.compile("gh workflow run")\n'
                               'def main(command):\n'
                               '    return 2 if R.search(command) else 0\n',
                               touch_inventory=True)
        self.assertEqual(code, 2)
        self.assertIn("Commit them separately", err)


class TestTheGuardAllows(GuardCase):
    """AC4, and the direction that costs the most when it is wrong.

    This guard sits on every commit touching .claude/hooks/, so a false
    positive stops all hook maintenance.
    """

    def test_a_trigger_rather_than_a_waiver(self):
        code, err = self.judge("trig_guard.py",
                               'def main(command):\n'
                               '    if "git commit" not in command:\n'
                               '        return 0\n'
                               '    return 2\n')
        self.assertEqual(code, 0, err)

    def test_ordinary_guard_maintenance(self):
        code, err = self.judge("plain2_guard.py",
                               'import re\n'
                               'R = re.compile("gh workflow run")\n'
                               'def main(command):\n'
                               '    return 2 if R.search(command) else 0\n')
        self.assertEqual(code, 0, err)

    def test_reading_the_environment(self):
        code, err = self.judge("env_guard.py",
                               'import os\n'
                               'def main(command):\n'
                               '    if os.environ.get("CI_RUN_OK") == "1":\n'
                               '        return 0\n'
                               '    return 2\n')
        self.assertEqual(code, 0, err)


class TestTheGuardDoesNotExemptItself(unittest.TestCase):
    """The first version skipped its own file so its documentation would not
    trip the scan, which handed the author the one file where a door could be
    written unwatched -- in the guard whose whole purpose is that the author
    cannot write himself a door.
    """

    def test_its_own_source_is_scanned_and_is_clean(self):
        with open(GUARD) as handle:
            self.assertEqual(waivers(handle.read()), [])

    def test_no_hook_in_this_repo_waives_on_an_unrecorded_token(self):
        """The live inventory agrees with the live hooks.

        This is the check the guard performs at commit time, asserted over
        the tree as it stands -- so a hatch that reaches any hook by a route
        that skips the commit gate is found by the suite as well.
        """
        with open(os.path.join(HOOKS, "hatch_inventory.json")) as handle:
            data = json.load(handle)
        known = {row.get("token")
                 for kind in ("launch_shell_env", "command_text_token",
                              "not_a_hatch")
                 for row in data.get(kind, [])}
        unrecorded = []
        for name in sorted(os.listdir(HOOKS)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(HOOKS, name)) as handle:
                for line, token in waivers(handle.read()):
                    if token not in known:
                        unrecorded.append(f"{name}:{line}: {token}")
        self.assertEqual(unrecorded, [])


def _pending_hatch_tokens():
    """Every token a launch_shell_env or command_text_token row records.

    Read from the inventory at run time rather than spelled here, the same
    reason SNEAK above is built instead of written: a token in this file
    would be a token this scan itself advertises to whatever reads it.
    """
    with open(os.path.join(HOOKS, "hatch_inventory.json")) as handle:
        data = json.load(handle)
    return [row["token"] for kind in ("launch_shell_env", "command_text_token")
            for row in data.get(kind, [])]


def _agent_loaded_text_files():
    """CLAUDE.md, CLAUDE.local.md, and every shared fragment they draw from.

    This is the text every agent in claude-env loads, and, through the
    symlinked fragments, what every companion repo loads too.
    """
    paths = [os.path.join(ROOT, "CLAUDE.md"),
             os.path.join(ROOT, "CLAUDE.local.md")]
    shared = os.path.join(ROOT, "shared", "claude-md")
    for name in sorted(os.listdir(shared)):
        if name.endswith(".md"):
            paths.append(os.path.join(shared, name))
    return [p for p in paths if os.path.isfile(p)]


def _root_call_name(func):
    """Walk an attribute chain (`os.environ.get` etc.) down to its root name."""
    while isinstance(func, ast.Attribute):
        func = func.value
    return func.id if isinstance(func, ast.Name) else None


def _mechanism_string_ids(tree):
    """id() of every string-constant node AC2 exempts as the mechanism.

    A guard has to hold the literal token SOMEWHERE to recognise it -- in a
    docstring explaining it, in the regex or os.* call that reads it, in an
    os.environ subscript, or as the left side of the same `in` test
    hatch_shape_scan.waivers() already treats as the shape of a check. What
    AC2 forbids is everywhere else: the strings a refusal actually prints.
    """
    exempt = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                              ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                exempt.add(id(body[0].value))
        elif isinstance(node, ast.Call):
            if _root_call_name(node.func) in ("re", "os"):
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        exempt.add(id(arg))
        elif isinstance(node, ast.Subscript):
            value = node.value
            if (isinstance(value, ast.Attribute) and value.attr == "environ"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "os"):
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    exempt.add(id(sl))
        elif (isinstance(node, ast.Compare) and node.ops
                and isinstance(node.ops[0], (ast.In, ast.NotIn))):
            left = node.left
            if isinstance(left, ast.Constant) and isinstance(left.value, str):
                exempt.add(id(left))
    return exempt


class TestNoPendingHatchIsAdvertised(unittest.TestCase):
    """CE-12.11, refiling CE-12.9. Being listed in hatch_inventory.json is
    not Patrick's approval -- every row reads "judged": "pending" until he
    rules on it. Advertising the spelling in text every agent loads, or in
    a hook's own output, hands out the key to a door nobody has agreed
    exists yet.
    """

    def test_agent_loaded_text_names_no_hatch_token(self):
        """AC1."""
        tokens = _pending_hatch_tokens()
        hits = []
        for path in _agent_loaded_text_files():
            rel = os.path.relpath(path, ROOT)
            with open(path) as handle:
                for lineno, line in enumerate(handle, 1):
                    for token in tokens:
                        if token in line:
                            hits.append(f"{rel}:{lineno}: {token}")
        self.assertEqual(hits, [])

    def test_no_hook_output_string_names_a_hatch_token(self):
        """AC2."""
        tokens = _pending_hatch_tokens()
        hits = []
        for name in sorted(os.listdir(HOOKS)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(HOOKS, name)
            with open(path) as handle:
                src = handle.read()
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            exempt = _mechanism_string_ids(tree)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)):
                    continue
                if id(node) in exempt:
                    continue
                for token in tokens:
                    if token in node.value:
                        hits.append(f"{name}:{node.lineno}: {token}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
