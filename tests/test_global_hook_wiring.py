#!/usr/bin/env python3
"""CE-2.100: the global hook wirings fail closed.

Every hook command in ~/.claude/settings.json used to be free to allow when it
could not run: `test -f <hook> || exit 0`, a bare `python3` or `bash` found on
a PATH whose first entry is agent-writable, or a bash script that exits 127
when missing. These tests read the LIVE settings file (from the password
database's home, never $HOME) and run each command three ways, none of which
runs a real hook:

- with its hook replaced by a missing path;
- with its pinned interpreter replaced by a missing one;
- with its hook replaced by a stub that exits 0.

What each exit means is per event (Claude Code's hooks doc, fetched
2026-09-27): exit 2 refuses a PreToolUse call and shows stderr on
PostToolUse; on Stop it prevents the stop and loops the turn, and on
SessionStart it is only a notice. So guards exit 2, and SessionStart, Stop
and advisory hooks exit 1 with a message saying they did not run.

Run directly: python3 tests/test_global_hook_wiring.py
"""
import json
import os
import pwd
import re
import subprocess
import tempfile
import unittest

SETTINGS = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".claude", "settings.json")
PY = "/usr/bin/python3"
BASH = "/bin/bash"
GUARD_EVENTS = {"PreToolUse", "PostToolUse"}
# Advisory hooks report instead of refusing, whatever their event.
ADVISORY = ("memory_scan_hook.py", "detect-orphan-installs.sh")
# Its Darwin gate stays until CE-2.104 decides it; on Linux it exits 0 first.
DARWIN_GATED = "ci_cost_guard.py"
HOOK_PATH = re.compile(r"/[\w./-]+\.(?:py|sh)\b")
BARE_INTERPRETER = re.compile(r"(?:^|[;&|{(]\s*)(python3?|bash|sh)\s")


def commands():
    with open(SETTINGS) as fh:
        settings = json.load(fh)
    found = []
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    found.append((event, hook["command"]))
    return found


def hook_of(command):
    paths = set(HOOK_PATH.findall(command))
    if len(paths) != 1:
        raise AssertionError(f"expected exactly one hook path in: {command}")
    return paths.pop()


def is_guard(event, command):
    return event in GUARD_EVENTS and not any(a in command for a in ADVISORY)


def run(command):
    return subprocess.run([BASH, "-c", command], input="{}", capture_output=True,
                          text=True, timeout=60)


class TestTheGlobalWiring(unittest.TestCase):

    def setUp(self):
        self.commands = commands()
        self.assertTrue(self.commands, f"no hook commands found in {SETTINGS}")
        self.tmp = tempfile.mkdtemp(prefix="wiring-")

    def test_every_interpreter_is_pinned(self):
        for event, command in self.commands:
            with self.subTest(command=command):
                self.assertIsNone(BARE_INTERPRETER.search(command),
                                  "a bare interpreter is found on PATH, and ~/.local/bin is first")
                hook = hook_of(command)
                pinned = PY if hook.endswith(".py") else BASH
                self.assertIn(f"{pinned} {hook}", command)

    def test_no_command_falls_back_to_an_allow(self):
        darwin = [c for _, c in self.commands if "|| exit 0" in c]
        self.assertEqual(len(darwin), 1, f"'|| exit 0' outside the Darwin gate: {darwin}")
        self.assertIn(DARWIN_GATED, darwin[0])
        self.assertIn('[ "$(uname)" = Darwin ] || exit 0', darwin[0])

    def test_a_missing_hook_refuses_or_says_so(self):
        for event, command in self.commands:
            if DARWIN_GATED in command:
                continue
            hook = hook_of(command)
            missing = os.path.join(self.tmp, "missing", os.path.basename(hook))
            with self.subTest(event=event, hook=os.path.basename(hook)):
                done = run(command.replace(hook, missing))
                if is_guard(event, command):
                    self.assertEqual(done.returncode, 2, done.stderr)
                else:
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("NOT run", done.stderr)
                    self.assertIn(os.path.basename(hook), done.stderr)

    def test_a_missing_interpreter_refuses_or_says_so(self):
        for event, command in self.commands:
            if DARWIN_GATED in command:
                continue
            hook = hook_of(command)
            pinned = PY if hook.endswith(".py") else BASH
            gone = os.path.join(self.tmp, "no-such-bin", os.path.basename(pinned))
            with self.subTest(event=event, hook=os.path.basename(hook)):
                done = run(command.replace(pinned, gone))
                if is_guard(event, command):
                    self.assertEqual(done.returncode, 2, done.stderr)
                else:
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("NOT run", done.stderr)

    def test_a_present_hook_runs(self):
        for event, command in self.commands:
            hook = hook_of(command)
            stub = os.path.join(self.tmp, "stub", os.path.basename(hook))
            os.makedirs(os.path.dirname(stub), exist_ok=True)
            with open(stub, "w") as fh:
                fh.write("import sys\nsys.exit(0)\n" if hook.endswith(".py") else "exit 0\n")
            with self.subTest(event=event, hook=os.path.basename(hook)):
                done = run(command.replace(hook, stub))
                self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
