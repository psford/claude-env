#!/usr/bin/env python3
"""
agent_worktree_sweep.py — SessionStart hook: removes an agent's isolation
worktree once the session that held it has ended and nothing in it is work
(CE-2.53).

Why: agent_worktree_default_guard forces isolation="worktree" on every Agent
dispatch, so Claude Code makes one worktree per agent at
<main>/.claude/worktrees/agent-<id>. Claude Code removes a clean one itself
when its agent finishes, and keeps (and later unlocks) a dirty one. What it
cannot clean is a worktree whose session died first -- a window reload, a
machine restart. Those stay registered and locked, and `git worktree list`
stops answering "where is work happening" (four, 15 MB, 2026-09-21; one was
mistaken for a dev's real workspace).

The signal, measured on Claude Code 2.1.270: while an agent runs, its
worktree is locked with the reason
    claude agent agent-<id> (pid <pid> start <ticks>)
where <pid> is the session's `claude` process and <ticks> is field 22 of
/proc/<pid>/stat. A lock whose pid is not alive with that same start time
belongs to a session that has ended. SubagentStop is no use here: it never
fires for a session that died, which is exactly the case that leaks.

Anything in the tree that is not exactly the committed checkout is work, and
ignored files count. The CSO's review of the first build (44cdaa4) showed a
plain `git status --porcelain` misses them, and `git worktree remove`
without --force deletes them; claude-env ignores *.md, so an agent's notes
were exactly that. A tree kept for its content is named at every session
start until someone removes it: a visible leftover, never a lost file.

The inputs, and what each does when missing, malformed or altered (the
numbered list in CE-2.53's description):
  1. stdin not a JSON object, or no usable cwd: nothing is done.
  2. cwd in no repository, or a bare/unknown layout: nothing is done.
  3. `git worktree list --porcelain -z` fails: nothing is done.
  4. Only a tree whose realpath's parent IS <main>/.claude/worktrees and
     whose name is agent-<id> is considered; a named dev worktree
     (<repo>--<ID>), anything nested deeper, or a symlink elsewhere is not.
  5. A tree whose own .git leads to another repository: kept.
  6. Unlocked: never removed (Claude Code kept it on purpose); named if it
     holds work. A lock it cannot parse, or no /proc: kept. A live holder
     (same pid, same start time): kept.
  7. Any process whose cwd is inside the tree: kept, named as in use.
  8. Any tracked change, untracked or ignored file, whatever the tree's own
     config says, or an index entry flagged assume-unchanged or
     skip-worktree: kept, named. A check that fails: kept.
  9. Otherwise: unlocked, then `git worktree remove` without --force; if
     either fails it is printed and nothing else is tried. Its branch,
     worktree-agent-<id>, is kept, so no commit is lost.
 10. Always exits 0: a cleanup that fails leaves things as they were and
     never blocks a session from starting.
"""
import json
import os
import re
import subprocess
import sys

LOCK_REASON = re.compile(r"^claude agent agent-[0-9a-z]+ \(pid (\d+) start (\d+)\)$")
AGENT_DIR = re.compile(r"^agent-[0-9a-z]+$")
GIT_TIMEOUT = 20

# Hook runners can inherit GIT_DIR and friends; every git call here names its
# repository explicitly and must not be redirected to another one.
_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

# Overrides a tree's own config that could hide content from the checks.
_SEE_EVERYTHING = ["-c", "core.fsmonitor=false",
                   "-c", "status.showUntrackedFiles=normal"]


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True, text=True, env=_ENV, timeout=GIT_TIMEOUT,
    )


def _common_dir(cwd):
    result = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if result.returncode != 0:
        return None
    return os.path.realpath(result.stdout.strip())


def _main_checkout(cwd):
    """(main working tree, its common dir) for the repository containing
    cwd, or None."""
    common = _common_dir(cwd)
    if common is None or os.path.basename(common) != ".git":
        return None  # bare repository, or a layout this hook does not know
    return os.path.dirname(common), common


def _worktrees(main):
    """[(path, locked, reason)] for every worktree git lists."""
    result = _git(main, "worktree", "list", "--porcelain", "-z")
    if result.returncode != 0:
        return []
    found = []
    path, locked, reason = None, False, ""
    # -z: each attribute ends in NUL and each record in an extra NUL.
    for field in result.stdout.split("\0"):
        if field.startswith("worktree "):
            path, locked, reason = field[len("worktree "):], False, ""
        elif field == "locked":
            locked = True
        elif field.startswith("locked "):
            locked, reason = True, field[len("locked "):]
        elif field == "" and path is not None:
            found.append((path, locked, reason))
            path = None
    return found


def _start_ticks(pid):
    """Field 22 of /proc/<pid>/stat, or None when no such process exists."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            stat = fh.read()
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = stat.rsplit(")", 1)[1].split()
    return int(fields[19])


def _holder_ended(reason):
    """True only when the lock's holder is provably gone; False when it is
    running or this hook cannot tell."""
    match = LOCK_REASON.match(reason)
    if not match or not os.path.isdir("/proc/self"):
        return False
    pid, start = int(match.group(1)), int(match.group(2))
    try:
        ticks = _start_ticks(pid)
    except (OSError, ValueError, IndexError):
        return False
    return ticks is None or ticks != start


def _process_inside(tree):
    """True if any readable process has its cwd inside tree."""
    prefix = tree + os.sep
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            cwd = os.path.realpath(os.readlink(f"/proc/{entry}/cwd"))
        except OSError:
            continue  # gone meanwhile, or another user's process
        if cwd == tree or cwd.startswith(prefix):
            return True
    return False


def _holds_work(tree):
    """True if the tree holds anything beyond the committed checkout, or if
    that cannot be established."""
    status = _git(tree, *_SEE_EVERYTHING, "status", "--porcelain",
                  "--untracked-files=normal", "--ignored")
    if status.returncode != 0 or status.stdout.strip():
        return True
    # A lower-case tag is assume-unchanged, S is skip-worktree: git status
    # does not look at either file's content.
    flags = _git(tree, *_SEE_EVERYTHING, "ls-files", "-v")
    if flags.returncode != 0:
        return True
    return any(line[:1].islower() or line[:1] == "S"
               for line in flags.stdout.splitlines())


def sweep(main, common):
    agents_dir = os.path.realpath(os.path.join(main, ".claude", "worktrees"))
    for path, locked, reason in _worktrees(main):
        real = os.path.realpath(path)
        if os.path.dirname(real) != agents_dir:
            continue
        if not AGENT_DIR.match(os.path.basename(real)):
            continue
        if _common_dir(real) != common:
            continue
        if not locked:
            if _holds_work(real):
                print(f"agent_worktree_sweep: kept {path}: unlocked, and it "
                      f"holds files that are not committed")
            continue
        if not _holder_ended(reason):
            continue
        if _process_inside(real):
            print(f"agent_worktree_sweep: kept {path}: its agent has ended "
                  f"but a process is still working in it")
            continue
        if _holds_work(real):
            print(f"agent_worktree_sweep: kept {path}: its agent has ended "
                  f"but it holds files that are not committed")
            continue
        unlocked = _git(main, "worktree", "unlock", path)
        if unlocked.returncode != 0:
            print(f"agent_worktree_sweep: kept {path}: its agent has ended "
                  f"but it could not be unlocked: {unlocked.stderr.strip()}")
            continue
        removed = _git(main, "worktree", "remove", path)
        if removed.returncode == 0:
            print(f"agent_worktree_sweep: removed {path}: its agent has ended")
        else:
            print(f"agent_worktree_sweep: could not remove {path}: "
                  f"{removed.stderr.strip()}")


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    if not isinstance(data, dict):
        return
    cwd = data.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        return
    found = _main_checkout(cwd)
    if found is None:
        return
    sweep(*found)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"agent_worktree_sweep: stopped early, nothing further removed: {exc}")
    sys.exit(0)
