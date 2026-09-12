#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Park before toss.

Background: 2026-07-08 (photo-portfolio emphasis span-layout, attempt 3).
A full day of code (layout engine + mount + tests, ~800 lines) was built,
rejected on visual review, and discarded via an uncommitted-tree wipe.
Zero git artifact survived. The only record is a hand-written prose entry
in docs/decisions.md. Git-based metrics/retros can't see the attempt, and
nothing of the code is available for a future attempt to diff against.

What this hook does:
- Fires on Bash commands that look like a bulk, uncommitted-work-destroying
  operation:
    * `git restore` (worktree forms — NOT a `--staged`-only unstage)
    * `git checkout -- <path>` / `git checkout .` / `git checkout HEAD -- `
    * `git clean -f...` (any -f-flavored clean)
    * `rm` targeting paths that currently carry uncommitted git state
- Estimates the size of what would be lost (changed/added lines via
  `git diff --shortstat` + untracked file line counts, scoped to the
  command's target path when one is given).
- BLOCKS (exit 2) if the estimated loss is >= threshold (default 150
  lines; override with PARK_MIN_LINES).
- Escape hatches:
    * Park it first: `~/projects/claude-env/helpers/park-work.sh <slug>`,
      then re-run the discard command.
    * Explicit bypass: `PARK_OK=1` env var, or a trailing
      `# PARK-OK: reason` comment on the same command line.
"""

import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    GIT_GLOBAL_FLAGS_WITH_VALUE, parse_sees_everything, resolved_commands,
    strip_heredoc_bodies)

# Commands that do NOT execute their arguments, so a discard phrase sitting
# inside one is data. This is the SAFE side, deliberately: it is small and
# knowable, while "everything that can execute a string" is neither. Anything
# absent from this set costs the raw-text match, which is the floor.
#
# The floor is the whole lesson of CE-2.25's first review. Narrowing this
# guard from text to tokens turned NINE real discards into silent passes --
# `script -qec`, `strace`, `valgrind`, write-then-`bash file`, a cat-heredoc,
# `python3 -c`, `ruby -e`. QA did not merely measure them: it ran them in
# throwaway repos and destroyed 200 lines of uncommitted work with no
# artifact, which is the exact loss this guard was written for. The old text
# match was crude and it was the floor; removing it was the defect.
INERT = frozenset({
    "git", "echo", "printf", "ticket", "grep", "rg", "cat", "ls", "head",
    "tail", "wc", "jq", "diff", "comm", "sort", "uniq",
    "basename", "dirname", "true", "false", "test",
})

# `sed` and `awk` were in that set and had to come out: GNU sed executes the
# replacement under the `s///e` flag, and awk executes through `system()`.
# Both were measured destroying a real worktree while the walk called them
# inert -- so "does not execute its arguments" was false of the very set that
# claims it (CE-2.25 QA round 2). They now cost the raw-text floor like any
# other executor, which is the recoverable direction: a sed or awk carrying
# the phrase in a non-executing position now false-positives, and this file
# already treats a wrong refusal as the cheap error.
#
# `git` stays, but every `-c` value it carries is judged as a token --
# see _git_runs_a_config_value.

DEFAULT_THRESHOLD = 150


def _git_discards(command):
    """Every real `git restore`/`git checkout` here, as (subcommand, args).

    Read as TOKENS, not as text. Until 2026-09-11 this was two regexes run
    against the whole command string, so ANY text containing the phrase was
    treated as the act -- and the refusal then stated, falsely, that the
    command would discard N lines of uncommitted work.

    Measured on this guard before the change: `git commit -m "...git
    restore..."` BLOCKED while the identical commit without those words in
    its message passed; `echo`, a ticket note, and `grep -rn "git restore"`
    all BLOCKED. A commit is the operation that PRESERVES uncommitted work,
    and a grep changes nothing. The guard was refusing the investigation of
    its own defect.

    This is the third instance of the class CE-2.20 removed from
    deploy_guard -- "a guard that fires on the mention of a thing rather
    than on the thing costs trust, which is the currency it needs to keep
    working." The refinements below this were always right; they just ran
    after a text match.

    Returns (hits, parsed). `parsed` is False when nothing could be read at
    all, and the caller falls back to the old text match rather than to
    silence: a command this cannot read is not a command it may approve.
    """
    found, parsed = resolved_commands(strip_heredoc_bodies(command or ""))
    hits = []
    for argv, _source, _remote in found:
        if not argv or os.path.basename(argv[0]) != "git":
            continue
        index = 1
        while index < len(argv):
            token = argv[index]
            if token in GIT_GLOBAL_FLAGS_WITH_VALUE:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            break
        if index >= len(argv):
            continue
        sub = argv[index]
        if sub in ("restore", "checkout"):
            hits.append((sub, argv[index + 1:]))
    return hits, parsed


RESTORE_RE = re.compile(r'\bgit\s+restore\b')
CHECKOUT_DISCARD_RE = re.compile(r'\bgit\s+checkout\s+(?:--\s|\.(?:\s|$)|HEAD\s+--\s)')
CLEAN_FORCE_RE = re.compile(r'\bgit\s+clean\b[^|;&]*-\w*f')
RM_RE = re.compile(r'(?:^|[;&|]\s*)rm\s+')
PARK_OK_INLINE = re.compile(r'#\s*PARK-OK\s*:', re.IGNORECASE)


def _run(args, cwd=None, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _discards_worktree(command):
    """True when a REAL restore/checkout here would touch the worktree."""
    hits, parsed = _git_discards(command)
    if not parsed:
        # Nothing tokenised: fall back to the old text match rather than to
        # silence. Being wrong here costs a false refusal, which is
        # recoverable; being silent costs the day of work this guard exists
        # to protect.
        return bool(RESTORE_RE.search(command)
                    or CHECKOUT_DISCARD_RE.search(command))
    for sub, args in hits:
        if sub == "restore":
            has_staged = "--staged" in args or "-S" in args
            has_worktree = "--worktree" in args or "-W" in args
            if has_staged and not has_worktree:
                continue  # unstage only -- index change, worktree untouched
            return True
        # checkout: only the pathspec forms discard. A branch switch does
        # not, and neither does `checkout -b`.
        if "--" in args or "." in args or (args and args[0] == "HEAD"):
            return True

    # No discard the walk could SEE. That is only an answer if the walk could
    # see everything -- otherwise the phrase is in there and something in
    # this command can execute a string the walk never read.
    if _walk_saw_everything(command):
        return False
    return bool(RESTORE_RE.search(command)
                or CHECKOUT_DISCARD_RE.search(command))


def _walk_saw_everything(command):
    """True only when nothing here can execute text the walk did not read.

    Every resolved command must be INERT, every statement must have resolved
    at all, and the shared parser must agree it is plainly commands and
    separators. An interpreter payload comes back as source rather than argv
    and can never satisfy this, which is correct: `python3 -c` handed back as
    a string is exactly the case that cost 200 lines under review.
    """
    if not parse_sees_everything(command):
        return False
    found, parsed = resolved_commands(strip_heredoc_bodies(command or ""))
    if not parsed or not found:
        return False
    for argv, _source, _remote in found:
        if argv is None:          # source payload, not shell -- unreadable
            return False
        argv0 = os.path.basename(argv[0])
        if argv0 not in INERT:
            return False
        if argv0 == "git" and _git_runs_a_config_value(argv):
            return False
    return True


def _git_runs_a_config_value(argv):
    """True when a `git -c name=value` pair can execute something.

    GIT_GLOBAL_FLAGS_WITH_VALUE skips a `-c` value as data, so the walk
    resolves the one-letter alias as the subcommand and never reads the
    payload at all.

    Judged on the TOKEN, which is the whole point. The first attempt was a
    regex over the raw command text: it matched `git -c alias.z='!...'` and
    missed `git -c "alias.z=!..."` and `git -c 'alias.z=!...'` -- the same
    escape with the quotes moved. shlex hands this function an identical
    token list for all three, so the tokens were already here and a text
    pattern was reached for instead. Both missed spellings destroyed 240
    real lines under review (CE-2.25 QA round 3).
    """
    values = []
    for index, token in enumerate(argv):
        if token == "-c" and index + 1 < len(argv):
            values.append(argv[index + 1])
        elif token.startswith("-c") and len(token) > 2:
            values.append(token[2:])

    for value in values:
        name, sep, payload = value.partition("=")
        if not sep:
            continue
        if name.strip().startswith("alias.") and payload.lstrip().startswith("!"):
            return True
        # Deliberately broader than the alias case: core.pager and
        # core.fsmonitor were both measured executing their values, so any
        # config value carrying a discard phrase costs the floor. A wrong
        # refusal here is the recoverable error; a wrong pass is a lost day.
        if RESTORE_RE.search(payload) or CHECKOUT_DISCARD_RE.search(payload):
            return True
    return False


def _line_count(path):
    try:
        with open(path, 'rb') as f:
            data = f.read(200_000)
        if b'\x00' in data:
            return 25  # binary-ish heuristic weight
        return data.count(b'\n') + 1
    except OSError:
        return 0


def _estimate_loss(cwd, pathspec=None):
    diff_args = ["git", "diff", "--shortstat", "HEAD"]
    status_args = ["git", "status", "--porcelain", "-uall"]
    if pathspec:
        diff_args += ["--", pathspec]
        status_args += ["--", pathspec]

    total = 0
    rc, out = _run(diff_args, cwd=cwd)
    if rc == 0 and out.strip():
        for pat in (r'(\d+)\s+insertion', r'(\d+)\s+deletion'):
            m = re.search(pat, out)
            if m:
                total += int(m.group(1))

    rc, out = _run(status_args, cwd=cwd)
    if rc == 0:
        for line in out.splitlines():
            if line.startswith('??'):
                fpath = line[3:].strip().strip('"')
                total += _line_count(os.path.join(cwd, fpath))
    return total


def _rm_targets(command):
    targets = []
    for chunk in re.split(r'[;&|]', command):
        chunk = chunk.strip()
        if not RM_RE.match(chunk + ' '):
            continue
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            continue
        for tok in tokens[1:]:
            if not tok.startswith('-'):
                targets.append(tok)
    return targets


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0
    if os.environ.get("PARK_OK") == "1" or PARK_OK_INLINE.search(command):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    threshold = int(os.environ.get("PARK_MIN_LINES", DEFAULT_THRESHOLD))
    reasons = []

    if _discards_worktree(command):
        loss = _estimate_loss(cwd)
        if loss >= threshold:
            reasons.append(("git restore/checkout (whole worktree)", loss))

    if CLEAN_FORCE_RE.search(command):
        loss = _estimate_loss(cwd)
        if loss >= threshold:
            reasons.append(("git clean -f...", loss))

    if RM_RE.search(command):
        rm_loss = 0
        for target in _rm_targets(command):
            abspath = target if os.path.isabs(target) else os.path.join(cwd, target)
            if not os.path.exists(abspath):
                continue
            rc, _ = _run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=os.path.dirname(abspath) or cwd,
            )
            if rc != 0:
                continue
            rm_loss += _estimate_loss(cwd, pathspec=target)
        if rm_loss >= threshold:
            reasons.append(("rm (uncommitted paths)", rm_loss))

    if not reasons:
        return 0

    biggest = max(reasons, key=lambda r: r[1])
    print(
        "\n[park_before_toss_guard] BLOCKED\n"
        f"This command would discard ~{biggest[1]} lines of uncommitted work "
        f"({biggest[0]}) — at/above the {threshold}-line park threshold.\n\n"
        "Park it before tossing it, so a rejected attempt still leaves a git\n"
        "artifact a future session can diff against:\n\n"
        "  ~/projects/claude-env/helpers/park-work.sh <slug>\n"
        "  # then re-run the discard command\n\n"
        "Bypass (only for genuinely disposable scratch work):\n"
        "  PARK_OK=1 <command>\n"
        "  or append  # PARK-OK: reason  to the command\n",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
