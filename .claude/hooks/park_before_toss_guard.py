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
    statements, strip_heredoc_bodies)

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
    "tail", "wc", "jq", "diff", "comm", "sort", "uniq", "tee",
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


def _floor_text(command):
    """What the raw-text floor is allowed to read.

    The floor exists so a command this cannot parse is refused rather than
    approved. It was reading the command verbatim, which meant a HEREDOC BODY
    counted as a command -- and a heredoc body is the most ordinary way there
    is to write a file whose contents happen to discuss the thing the guard
    watches for.

    That is not theoretical. It refused the command writing the probe that
    was to verify this guard (CE-2.25, 2026-09-12), which is AC1's own defect
    wearing different clothes: the phrase was in an argument, not in an act.

    strip_heredoc_bodies knows `bash <<EOF` feeds a shell and keeps that body.
    It does NOT see `cat <<EOF | bash`, where the shell is on the far side of
    a pipe -- round 1's cat-heredoc-then-bash escape, which must stay refused.

    So the body is dropped only when NOTHING in the command could run it:
    every command here is INERT, the same set the walk already trusts. A
    `cat > probe.py <<EOF` is all inert and its body is content. Put a `|
    bash` on the end and it is not, and the floor reads the whole thing.

    Asking INERT rather than listing the ways a shell can be reached keeps
    this on the finite side, which is the entire subject of this ticket.
    """
    text = command or ""
    stripped = strip_heredoc_bodies(text)
    found, parsed = resolved_commands(stripped)
    if not parsed:
        return text
    # Stripping a body leaves its terminator line behind, and a bare `EOF`
    # reads as a command head that is in nothing's allowlist. Skip the
    # delimiters this command actually declares rather than trusting a name.
    delimiters = set(HEREDOC_DELIM.findall(text))
    for argv, _source, _remote in found:
        if argv is None:
            return text
        head = os.path.basename(argv[0])
        if head in delimiters:
            continue
        if head not in INERT:
            return text
    return stripped


HEREDOC_DELIM = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)")


def _discards_worktree(command):
    """True when a REAL restore/checkout here would touch the worktree."""
    hits, parsed = _git_discards(command)
    if not parsed:
        # Nothing tokenised: fall back to the old text match rather than to
        # silence. Being wrong here costs a false refusal, which is
        # recoverable; being silent costs the day of work this guard exists
        # to protect.
        floor = _floor_text(command)
        return bool(RESTORE_RE.search(floor)
                    or CHECKOUT_DISCARD_RE.search(floor))
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

    # No discard in the SUBCOMMANDS. Two questions are left, and they are not
    # the same question: did the walk read a discard somewhere the subcommand
    # scan does not look, and could the walk see everything at all.
    seen, saw_everything = _walk_verdict(command)
    if seen:
        return True
    if saw_everything:
        return False
    floor = _floor_text(command)
    return bool(RESTORE_RE.search(floor)
                or CHECKOUT_DISCARD_RE.search(floor))


def _walk_verdict(command):
    """(a discard the walk READ, whether the walk could see everything).

    Both answers come out of one walk because both come from the same tokens.
    Separating them is the round-4 fix, and the separation is the whole point:

      * a `-c` value that can EXECUTE something -- an `alias.*` starting `!`,
        or core.pager, or core.fsmonitor -- means the walk did not see
        everything, so the raw-text floor decides;
      * a `-c` value that IS a discard means the walk read the act itself, and
        that is a refusal outright.

    Conflating the two is what let `git -c alias.z=\\!git\\ restore\\ . z`
    through. Its token says `alias.z=!git restore .` in plain text, so the
    walk read the discard -- but the old code only demoted to the raw floor,
    and the raw floor sees `git\\ restore\\ .`, where the backslashes break
    the phrase. The guard knew, and then asked something that did not.

    Every resolved command must be INERT, every statement must have resolved
    at all, and the shared parser must agree it is plainly commands and
    separators. An interpreter payload comes back as source rather than argv
    and can never satisfy this, which is correct: `python3 -c` handed back as
    a string is exactly the case that cost 200 lines under review.
    """
    if _assignment_carries_the_act(command):
        # Read BEFORE the walk, because the walk drops these. resolved_commands
        # and parse_sees_everything both strip a leading NAME=value as shell
        # noise, so the phrase-bearing token is gone before anything judges it:
        #   GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.z \
        #     GIT_CONFIG_VALUE_0='!git restore .' git z
        #   GIT_EDITOR='git restore .' git commit
        # QA measured the first destroying a real worktree (CE-2.25 round 4).
        # An assignment is not noise when its VALUE is the act.
        return True, False
    if not parse_sees_everything(command):
        return False, False
    found, parsed = resolved_commands(strip_heredoc_bodies(command or ""))
    if not parsed or not found:
        return False, False

    saw_everything = True
    for argv, _source, _remote in found:
        if argv is None:          # source payload, not shell -- unreadable
            saw_everything = False
            continue
        argv0 = os.path.basename(argv[0])
        if argv0 == "git":
            if _git_is_handed_the_act(argv):
                return True, False
        if argv0 not in INERT:
            saw_everything = False
    return False, saw_everything


def _assignment_carries_the_act(command):
    """True when a NAME=value prefix holds a discard the walk will discard.

    Same finite side as _git_is_handed_the_act: the phrase has to arrive in a
    TOKEN, so read the tokens. This one reads the ones the shared walk throws
    away before it starts.
    """
    for statement in statements(strip_heredoc_bodies(command or "")):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        for token in tokens:
            name, sep, value = token.partition("=")
            if not sep or not name or not ASSIGNMENT_NAME.match(name):
                break     # past the assignment prefix; the walk sees the rest
            if RESTORE_RE.search(value) or CHECKOUT_DISCARD_RE.search(value):
                return True
    return False


ASSIGNMENT_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


# The SAFE side, enumerated on purpose. For each git subcommand, the places a
# discard phrase is TEXT rather than an instruction. Everything not listed
# here is a place git might act on what it is given.
#
# `None` means every operand of that subcommand is text.
#
# This is the direction Grace argued for and the direction CE-13.6 took the
# other two guards. A name missing from a DANGEROUS-side list is a silent
# pass that destroys a day's work; a name missing from THIS list is a visible
# refusal, arguable and one line to fix. Four rounds of QA on this file were
# spent adding to a dangerous-side list -- `-c`, then two quote spellings,
# then a backslash -- while `git config`, `GIT_CONFIG_*` and `GIT_EDITOR` sat
# untouched behind it.
GIT_TEXT_POSITIONS = {
    "commit": ("-m", "--message"),
    "tag": ("-m", "--message"),
    "notes": ("-m", "--message"),
    "stash": ("-m", "--message"),
    "merge": ("-m", "--message"),
    "revert": ("-m", "--message"),
    "cherry-pick": ("-m", "--message"),
    "log": ("-S", "-G", "--grep", "--author", "--committer"),
    "rev-list": ("-S", "-G", "--grep", "--author", "--committer"),
    "grep": None,
    "branch": ("-m", "--message"),
}


def _git_is_handed_the_act(argv):
    """True when a git invocation carries a discard phrase somewhere git may run it.

    ONE question over every token, instead of a list of the mechanisms that
    deliver one. Rounds 2 through 5 of CE-2.25 each added a mechanism:

      * `git -c alias.z='!git restore .' z`, then the same with the quotes
        moved, then the same spelled with backslashes;
      * `git config alias.z '!git restore .' && git z`, which plants the
        alias in the repo's config file instead of on the command line;
      * `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.z
        GIT_CONFIG_VALUE_0='!git restore .' git z`, which sets config from
        the environment -- and whose phrase-bearing token `_repo_context`
        strips as a leading assignment before the walk ever sees it;
      * `GIT_EDITOR='git restore .' git commit`.

    QA measured the first three destroying a real worktree. Each fix closed
    exactly the spelling it was shown. There is no end to that list, because
    git reads config from the command line, from the environment, and from
    files, and it will grow more ways.

    The finite side is the other one: a phrase git might EXECUTE has to
    arrive in a token of this command, and the tokens where such a phrase is
    merely text are few and known. So scan them all, and excuse only the
    text positions.

    This SUBSUMES the `-c` check it replaces -- a `-c` value is simply a
    token that is not a text position -- which is why that function is gone
    rather than joined by three more.
    """
    text_flags = ()
    everything_is_text = False
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
    if index < len(argv) and argv[index] in GIT_TEXT_POSITIONS:
        positions = GIT_TEXT_POSITIONS[argv[index]]
        if positions is None:
            everything_is_text = True
        else:
            text_flags = positions

    for position, token in enumerate(argv):
        if not (RESTORE_RE.search(token) or CHECKOUT_DISCARD_RE.search(token)):
            continue
        if everything_is_text:
            continue
        previous = argv[position - 1] if position else ""
        if previous in text_flags:
            continue
        if any(token.startswith(flag + "=") for flag in text_flags):
            continue
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

    # CE-12.2, AC3. What stood here told the reader to park and re-run, and
    # this function never looks at refs/parked/ -- so the instruction could
    # not work, and the only thing that did work was the inline token printed
    # two lines below it. A refusal that misdirects and then hands over its
    # own key is how a session learns to reach for hatches; it is the
    # CWD_DRIFT_OK shape exactly. The mechanisms are unchanged and stay
    # pending Patrick's ruling in hatch_inventory.json. The advertisement is
    # what goes.
    biggest = max(reasons, key=lambda r: r[1])
    print(
        "\n[park_before_toss_guard] BLOCKED\n"
        f"This command would discard ~{biggest[1]} lines of uncommitted work "
        f"({biggest[0]}) — at/above the {threshold}-line park threshold.\n\n"
        "Park it first, so a rejected attempt still leaves a git artifact a\n"
        "future session can diff against:\n\n"
        "  ~/projects/claude-env/helpers/park-work.sh <slug>\n\n"
        "Parking does NOT clear this block, and nothing you can type will.\n"
        "If the block is wrong, fix this guard so it stops being wrong, or\n"
        "report it and stop — the shared rules under 'a wrong block is a\n"
        "defect, not a detour'. If the work is genuinely disposable, Patrick\n"
        "runs the discard from his own terminal.\n",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
