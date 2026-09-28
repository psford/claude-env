#!/usr/bin/env python3
"""Tests for .claude/hooks/session_integrity.py (CE-2.103).

A SessionStart exit 2 is only a notice (Claude Code's hooks doc), so the
plugin cache check (CE-2.101) and the hook wiring can drift in an interactive
session with nothing stopping it. session_integrity.py closes that:

- at SessionStart it ALWAYS writes a record for its session, clean or not;
- as a PreToolUse guard it refuses every tool call unless this session's
  record exists, parses, and says both the cache and the wiring are clean.

The CSO's list review of CE-2.103 set the semantics: an unconditional write
and refuse-on-missing (finding 2), and per-session records (finding 3).

Every test builds its own home under a temp dir, never the real ~/.claude.

Run: python3 .claude/hooks/tests/test_session_integrity.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HOOKS)
import session_integrity as si  # noqa: E402

SID = "11111111-2222-3333-4444-555555555555"
OTHER = "99999999-8888-7777-6666-555555555555"
HOOKS_SECTION = {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "test -x /usr/bin/python3 || exit 2; /usr/bin/python3 /x/g.py"}]}]}


class Home:
    """A home with live settings and a committed mirror to compare them to."""

    def __init__(self, case, live_hooks=None, mirror_hooks=None):
        self.root = tempfile.mkdtemp(prefix="si-")
        case.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        os.makedirs(os.path.join(self.home, ".claude"))
        self.settings = os.path.join(self.home, ".claude", "settings.json")
        self.mirror = os.path.join(self.root, "user-settings.json")
        with open(self.settings, "w") as fh:
            json.dump({"hooks": HOOKS_SECTION if live_hooks is None else live_hooks,
                       "model": "live-only"}, fh)
        with open(self.mirror, "w") as fh:
            json.dump({"hooks": HOOKS_SECTION if mirror_hooks is None else mirror_hooks}, fh)

    def records(self):
        return os.path.join(self.home, ".local", "share", "harness", "session-integrity")

    def record(self, sid=SID):
        return os.path.join(self.records(), f"{sid}.json")

    def write(self, sid=SID, cache=(True, ["verified: x"]), event="SessionStart"):
        payload = {"hook_event_name": event}
        if sid is not None:
            payload["session_id"] = sid
        fake = mock.Mock(side_effect=cache) if isinstance(cache, Exception) \
            else mock.Mock(return_value=cache)
        err = io.StringIO()
        with mock.patch.object(si.plugin_cache_integrity, "check", fake), \
                mock.patch.object(sys, "stderr", err):
            code = si.write_record(payload, home=self.home, mirror=self.mirror)
        return code, err.getvalue()

    def guard(self, sid=SID):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}}
        if sid is not None:
            payload["session_id"] = sid
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            code = si.guard(payload, home=self.home)
        return code, err.getvalue()


class TestTheSessionStartWriter(unittest.TestCase):

    def test_it_always_writes_a_record_for_its_session(self):
        h = Home(self)
        code, err = h.write()
        self.assertEqual(code, 0, err)
        rec = json.load(open(h.record()))
        self.assertIs(rec["cache_ok"], True)
        self.assertIs(rec["wiring_ok"], True)
        # Drift writes a record too, false, with the failing lines.
        h2 = Home(self, mirror_hooks={"PreToolUse": []})
        code, err = h2.write(cache=(False, ["BLOCKED: drift", "- x: changed"]))
        rec = json.load(open(h2.record()))
        self.assertFalse(rec["cache_ok"])
        self.assertFalse(rec["wiring_ok"])
        self.assertIn("- x: changed", "\n".join(rec["lines"]))
        self.assertNotEqual(code, 0)
        # A missing or malformed session id writes nothing, and says so.
        for bad in (None, "not-a-uuid", SID + "/../../x"):
            with self.subTest(session_id=bad):
                h3 = Home(self)
                code, err = h3.write(sid=bad)
                self.assertNotEqual(code, 0)
                self.assertIn("session id", err)
                self.assertFalse(os.path.exists(h3.records())
                                 and os.listdir(h3.records()))
        # Other sessions' records older than 7 days are swept; younger stay.
        h4 = Home(self)
        os.makedirs(h4.records())
        old, young = h4.record(OTHER), h4.record("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        for path in (old, young):
            with open(path, "w") as fh:
                fh.write("{}")
        eight_days = time.time() - 8 * 24 * 3600
        os.utime(old, (eight_days, eight_days))
        h4.write()
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(young))
        self.assertTrue(os.path.exists(h4.record()))

    def test_a_check_that_cannot_run_writes_a_drift_record(self):
        # The cache check raising is a drift record, not a missing one.
        h = Home(self)
        code, err = h.write(cache=RuntimeError("check crashed"))
        rec = json.load(open(h.record()))
        self.assertFalse(rec["cache_ok"])
        self.assertIn("check crashed", "\n".join(rec["lines"]))
        self.assertNotEqual(code, 0)
        # Unreadable live settings or mirror: wiring_ok false, record written.
        for broken in ("settings", "mirror"):
            with self.subTest(broken=broken):
                h2 = Home(self)
                with open(h2.settings if broken == "settings" else h2.mirror, "w") as fh:
                    fh.write("{not json")
                h2.write()
                rec = json.load(open(h2.record()))
                self.assertFalse(rec["wiring_ok"])
                self.assertTrue(rec["cache_ok"])


class TestTheGuard(unittest.TestCase):

    def test_a_clean_record_for_this_session_passes(self):
        h = Home(self)
        h.write()
        code, err = h.guard()
        self.assertEqual(code, 0, err)

    def test_a_missing_bad_or_drifted_record_refuses(self):
        cases = {}
        h = Home(self)                                  # no record at all
        cases["missing"] = h
        h = Home(self)
        h.write()
        with open(h.record(), "w") as fh:
            fh.write("{not json")
        cases["unreadable"] = h
        h = Home(self)
        h.write(cache=(False, ["BLOCKED: drift"]))
        cases["cache drift"] = h
        h = Home(self, mirror_hooks={"PreToolUse": []})
        h.write()
        cases["wiring drift"] = h
        h = Home(self)
        h.write(sid=OTHER)                              # another session's only
        cases["other session only"] = h
        for name, home in cases.items():
            with self.subTest(name):
                code, err = home.guard()
                self.assertEqual(code, 2, f"{name}: {err}")
                self.assertIn("BLOCKED", err)
        # A missing or malformed session id in the guard's own payload.
        h = Home(self)
        h.write()
        for bad in (None, "nope", SID + "/../x"):
            with self.subTest(guard_session_id=bad):
                code, err = h.guard(sid=bad)
                self.assertEqual(code, 2, err)
        # A record with non-boolean flags is not clean.
        h = Home(self)
        h.write()
        rec = json.load(open(h.record()))
        rec["cache_ok"] = "true"
        with open(h.record(), "w") as fh:
            json.dump(rec, fh)
        code, err = h.guard()
        self.assertEqual(code, 2, err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
