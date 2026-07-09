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

DEFAULT_THRESHOLD = 150

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


def _is_worktree_restore(command):
    if not RESTORE_RE.search(command):
        return False
    has_staged = '--staged' in command or re.search(r'(?<!\w)-S(?!\w)', command)
    has_worktree = '--worktree' in command or re.search(r'(?<!\w)-W(?!\w)', command)
    if has_staged and not has_worktree:
        return False  # unstage only — index change, worktree untouched
    return True


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

    if _is_worktree_restore(command) or CHECKOUT_DISCARD_RE.search(command):
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
