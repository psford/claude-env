#!/usr/bin/env python3
"""A per-session integrity record, and the guard that reads it (CE-2.103).

WHY THIS EXISTS. CE-2.101 checks the installed plugin cache at SessionStart,
but a SessionStart hook cannot block anything: its exit 2 "shows stderr to
user only", and the session proceeds (Claude Code's hooks doc; re-measured
2026-09-28, scratch/CE-2.103/). So in an interactive session a drifted cache,
or a hook wiring rolled back to fail-open, was a notice and nothing more.

This makes it a gate, in two halves of one module:

- SessionStart (the writer): ALWAYS writes a record for this session --
  clean or drifted -- to <passwd home>/.local/share/harness/session-integrity/
  <session_id>.json: {checked_at, cache_ok, wiring_ok, lines}. cache_ok is
  plugin_cache_integrity.check(); wiring_ok is the live ~/.claude/settings.json
  `hooks` section equalling the committed mirror's (CE-2.108 keeps the mirror
  current). A check that cannot run writes False, never nothing.
- PreToolUse (the guard): refuses every tool call unless THIS session's record
  exists, parses, and has cache_ok and wiring_ok both exactly True.

Refuse-on-missing is the point (the CSO's list review, finding 2): an unwired
writer, a deleted record or a failed write all refuse, loudly, instead of
reading as "clean". Records are per session (finding 3), so one session's
clean start never clears another session's drift; the id comes from the hook
payload and is fullmatched before it touches a path.

ROLLOUT ORDER (a missing record refuses everything): wire the SessionStart
writer first, start a session (or /clear, or resume) so it writes a record,
and only then wire the guard. Wiring the guard into a session with no record
refuses that session's every tool call until it restarts. Two probes belong to
wiring day, before the guard row goes in: that a subagent's tool calls carry
the parent's session_id (else every subagent call refuses), and that /clear
fires SessionStart on the live build.

Stated limits: a tripwire, not proof.
- The record, this file, plugin_cache_integrity.py, the mirror and the
  settings are all writable by the same account through Bash; a same-account
  adversary can forge a clean record.
- The record is a snapshot taken at session start. Drift that begins
  mid-session is judged at the next session start, not at the next tool call.
- A session older than 7 days loses its record to the next session's sweep,
  and its next tool call refuses until it restarts.
It catches drift present at start and careless edits, and it makes a deleted
record, or a missing cache check, loud.

Usage (settings.json): `/usr/bin/python3 <this file>` on SessionStart and on
PreToolUse; the event is read from the payload's hook_event_name.
"""
import json
import os
import pwd
import re
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The import is inside the fail-closed envelope: a missing or broken cache
# check must not make both halves exit 1, which PreToolUse treats as a pass.
try:
    import plugin_cache_integrity  # noqa: E402
    IMPORT_ERROR = None
except BaseException as _exc:
    plugin_cache_integrity = None
    IMPORT_ERROR = f"{type(_exc).__name__}: {_exc}"

SESSION_ID = re.compile(r"[0-9a-f-]{36}")
SWEEP_SECONDS = 7 * 24 * 3600
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIRROR = os.path.join(REPO_ROOT, "infrastructure", "claude-settings", "user-settings.json")


def passwd_home():
    """The account's home from the password database, as plugin_cache_integrity
    reads it; kept here so a broken import still finds the records."""
    return pwd.getpwuid(os.getuid()).pw_dir


def records_dir(home):
    return os.path.join(home, ".local", "share", "harness", "session-integrity")


def _session_id(payload):
    sid = payload.get("session_id") if isinstance(payload, dict) else None
    return sid if isinstance(sid, str) and SESSION_ID.fullmatch(sid) else None


def _hooks_of(path):
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        raise ValueError(f"{path} has no hooks object")
    return data["hooks"]


def _wiring(home, mirror):
    """(ok, lines): the live hooks section equals the mirror's."""
    live = os.path.join(home, ".claude", "settings.json")
    try:
        live_hooks, mirror_hooks = _hooks_of(live), _hooks_of(mirror)
    except (OSError, ValueError) as exc:
        return False, [f"wiring: cannot compare {live} with {mirror}: {exc}"]
    if live_hooks == mirror_hooks:
        return True, []
    events = sorted(set(live_hooks) | set(mirror_hooks))
    differ = [e for e in events if live_hooks.get(e) != mirror_hooks.get(e)]
    return False, [
        f"wiring: the live hooks differ from the committed mirror in {', '.join(differ)}.",
        f"  If the live wiring is the reviewed one, re-capture it: "
        f"{os.path.join(REPO_ROOT, 'helpers', 'sync-user-settings.sh')}",
        "  If it is not, restore the reviewed wiring from the mirror.",
    ]


def _sweep(directory, own):
    now = time.time()
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not name.endswith(".json") or name == own:
            continue
        path = os.path.join(directory, name)
        try:
            if now - os.path.getmtime(path) > SWEEP_SECONDS:
                os.remove(path)
        except OSError:
            continue


def write_record(payload, home=None, mirror=MIRROR):
    """The SessionStart half. 0 when clean, 2 (a notice) on drift, 1 when no
    record could be written at all."""
    home = home or passwd_home()
    sid = _session_id(payload)
    if sid is None:
        print("session_integrity: the SessionStart payload has no valid session id, so "
              "no record was written; every tool call in this session will be refused.",
              file=sys.stderr)
        return 1
    try:
        if plugin_cache_integrity is None:
            raise ImportError(f"plugin_cache_integrity cannot be imported: {IMPORT_ERROR}")
        cache_ok, cache_lines = plugin_cache_integrity.check(home=home)
    except Exception as exc:
        cache_ok, cache_lines = False, [f"cache: the check could not run: "
                                        f"{type(exc).__name__}: {exc}"]
    wiring_ok, wiring_lines = _wiring(home, mirror)
    record = {"checked_at": time.time(), "cache_ok": cache_ok is True,
              "wiring_ok": wiring_ok is True, "lines": list(cache_lines) + list(wiring_lines)}
    directory = records_dir(home)
    try:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{sid}.json")
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as fh:
            json.dump(record, fh)
        os.replace(tmp, path)
    except OSError as exc:
        print(f"session_integrity: could not write the session record: {exc}; every "
              "tool call in this session will be refused.", file=sys.stderr)
        return 1
    _sweep(directory, f"{sid}.json")
    if record["cache_ok"] and record["wiring_ok"]:
        return 0
    print("session_integrity: this session starts on a drifted plugin cache or hook "
          "wiring, and every tool call will be refused until it is fixed:", file=sys.stderr)
    for line in record["lines"]:
        print(f"  {line}", file=sys.stderr)
    return 2


def guard(payload, home=None):
    """The PreToolUse half. 0 only on a clean record for this session."""
    if plugin_cache_integrity is None:
        return _refuse(f"plugin_cache_integrity cannot be imported ({IMPORT_ERROR}), so the "
                       "cache check this guard stands on is missing or broken.")
    home = home or passwd_home()
    sid = _session_id(payload)
    if sid is None:
        return _refuse("the tool call's payload carries no valid session id, so this "
                       "session's integrity record cannot be found.")
    path = os.path.join(records_dir(home), f"{sid}.json")
    try:
        with open(path) as fh:
            record = json.load(fh)
    except FileNotFoundError:
        return _refuse(f"this session has no integrity record at {path}. The SessionStart "
                       "check did not run or was removed. Start a new session (or /clear) so "
                       "it runs, and check that ~/.claude/settings.json wires it.")
    except (OSError, ValueError) as exc:
        return _refuse(f"this session's integrity record at {path} cannot be read: {exc}.")
    if not isinstance(record, dict):
        return _refuse(f"this session's integrity record at {path} is not an object.")
    if record.get("cache_ok") is True and record.get("wiring_ok") is True:
        return 0
    lines = record.get("lines") if isinstance(record.get("lines"), list) else []
    return _refuse("this session started on a drifted plugin cache or hook wiring:\n"
                   + "\n".join(f"  {line}" for line in lines)
                   + "\n  Fix it (claude plugin update, or restore the reviewed wiring), "
                     "then start a new session.")


def _refuse(why):
    print(f"BLOCKED by session_integrity: {why}", file=sys.stderr)
    return 2


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return _refuse("the hook payload is not JSON, so this session cannot be identified.")
    try:
        if isinstance(payload, dict) and payload.get("hook_event_name") == "SessionStart":
            return write_record(payload)
        return guard(payload)
    except BaseException:
        traceback.print_exc()
        return _refuse("session_integrity crashed, and refuses rather than pass.")


if __name__ == "__main__":
    sys.exit(main())
