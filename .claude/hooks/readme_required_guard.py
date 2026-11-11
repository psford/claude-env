#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: a feature PR ships its README update.

Refuses `gh pr create` when the PR's branch changes 50 or more lines of code
and leaves the repo's README untouched. Patrick, 2026-11-10: "Updates to the
readme be required and shipped alongside code updates." It follows
spec_staleness_guard (code moved, the spec did not), but it refuses rather than
reminds, and it acts when the PR opens, the last point where the README can
still go in the same PR.

What it judges:
- Every repo with a README at its root (README, README.md, README.en.md, any
  case). A repo without one has nothing to keep current and is skipped. A
  branch that deletes it is refused.
- Every PR except a release PR whose head is develop: the feature PRs it
  carries were each judged when they opened. On a trunk repo, where features go
  straight to main, every PR is a feature PR. `--help` and `--dry-run` create
  nothing and pass.
- Code is every changed file that is not known to be something else (the safe
  default, specs/guards.md "Hooks fail closed"). Not code: documentation
  (*.md, *.rst, *.txt other than CMakeLists.txt, a top-level docs/ or doc/,
  LICENSE, CHANGELOG), tests and fixtures (tests/, test/, __tests__/, fixtures/
  at any depth, *.test.*, *.spec.*, test_*.py, *_test.*), repo tooling (.claude/,
  .github/), lock files and binaries. Renames count as a delete and an add.
- The threshold is 50 changed lines (added plus removed) across the branch, the
  same bar spec_staleness_guard uses. Patrick chose it so a small fix passes.
- The README counts as updated when its diff changes more than whitespace.

It fails closed: a PR it cannot judge (no repo, no base it can find, a branch
it cannot see, a --repo that matches none of this checkout's remotes, a value
computed by the shell, a PR opened on another machine or from inside a script,
or any error of its own) is refused, and the message says why and what to do.
A cold review on 2026-11-10 found the first version failed open on its own
crashes, misread renames, and missed attached short flags; all three are fixed.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    enter_target_repo, gh_subcommand_at, resolved_commands, strip_heredoc_bodies,
)

THRESHOLD = 50
PR_CREATE_TEXT = re.compile(r'\bgh\b[^|;]*\bpr\b[^|;]*\bcreate\b')
README = re.compile(r'^readme(?:[._-][^/]*)?$', re.IGNORECASE)
NOT_CODE = re.compile(
    r'^(?:docs?|\.claude|\.github)/'
    r'|(?:^|/)(?:tests?|__tests__|fixtures?)/'
    r'|\.(?:md|markdown|rst|adoc)$'
    r'|(?:^|/)(?!CMakeLists\.txt$)[^/]*\.txt$'
    r'|(?:^|/)(?:LICENSE|LICENCE|CHANGELOG|NOTICE)(?:\.[^/]*)?$'
    r'|(?:^|/)[^/]*\.(?:test|spec)\.[^/]+$'
    r'|(?:^|/)test_[^/]*\.py$'
    r'|(?:^|/)[^/]*_test\.[^/]+$'
    r'|(?:^|/)(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock'
    r'|Cargo\.lock|Gemfile\.lock|composer\.lock|go\.sum|uv\.lock|[^/]*\.lock)$',
    re.IGNORECASE)
COMPUTED = re.compile(r'[$`]')


class CantJudge(Exception):
    """A PR this guard can't judge: refused with `why` and `fix`."""

    def __init__(self, why, fix):
        super().__init__(why)
        self.why, self.fix = why, fix


def git(*args):
    """stdout of a git command, or None if it failed."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True,
                             errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def flag(argv, long, short):
    """The value of a gh flag in any of cobra's spellings, or None:
    `--head x`, `--head=x`, `-H x`, `-Hx`, `-H=x`."""
    for i, token in enumerate(argv):
        if token in (long, short):
            return argv[i + 1] if i + 1 < len(argv) else None
        if token.startswith(long + "="):
            return token.split("=", 1)[1]
        if token.startswith(short) and len(token) > 2 and not token.startswith("--"):
            return token[2:].lstrip("=")
    return None


def literal(value, what):
    if value is not None and COMPUTED.search(value):
        raise CantJudge(f"this PR's {what} is computed by the shell ({value}), so the README check can't tell what it is.",
                        f"Pass the {what} as plain text.")
    return value


def refuse(why, fix):
    print(f"Refused: {why}\n{fix}", file=sys.stderr)
    return 2


def first_ref(*candidates):
    for ref in candidates:
        if git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def numstat(*args):
    """{path: lines changed, or None for a binary} for a diff, renames as a delete and an add."""
    out = git("diff", "--numstat", "--no-renames", "-z", *args)
    if out is None:
        return None
    files = {}
    for record in out.split("\0"):
        parts = record.split("\t", 2)
        if len(parts) == 3:
            added, removed, path = parts
            files[path] = None if added == "-" else int(added) + int(removed)
    return files


def judge(argv):
    """0 to let this `gh pr create` through, 2 (with the reason) to refuse it."""
    if "--help" in argv or "-h" in argv or "--dry-run" in argv:
        return 0  # nothing is created
    if git("rev-parse", "--show-toplevel") is None:
        raise CantJudge("the command doesn't run in a git checkout.",
                        "Run gh pr create from a checkout of the repo the PR is for.")

    repo = literal(flag(argv, "--repo", "-R"), "repo") or os.environ.get("GH_REPO")
    if repo:
        urls = [git("remote", "get-url", r) or "" for r in (git("remote") or "").split()]
        if not any(re.search(rf'[/:]{re.escape(repo)}(?:\.git)?/?$', u.strip(), re.IGNORECASE) for u in urls):
            raise CantJudge(f"this PR is for {repo}, and none of this checkout's remotes is.",
                            f"Run gh pr create from a checkout of {repo} or a fork of it with {repo} as a remote.")

    head = literal(flag(argv, "--head", "-H"), "head branch")
    if head:
        head = head.split(":", 1)[-1]
    else:
        head = (git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    if not head or head == "HEAD":
        raise CantJudge("there's no branch checked out and no --head.", "Check out the PR's branch, or pass --head <branch>.")
    if head == "develop":
        return 0  # a release PR: the features it carries were judged when they opened

    base = literal(flag(argv, "--base", "-B"), "base branch")
    if not base:
        default = (git("symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "").strip()
        base = default.split("/", 1)[-1] if default else None
    if not base:
        raise CantJudge("there's no --base, and origin's default branch isn't known here.",
                        "Pass --base <branch>, or run `git remote set-head origin --auto` once in this checkout.")

    base_ref = first_ref(f"refs/remotes/origin/{base}", f"refs/heads/{base}")
    head_ref = first_ref(f"refs/heads/{head}", f"refs/remotes/origin/{head}")
    if not base_ref or not head_ref:
        raise CantJudge(f"this checkout has no branch {base if not base_ref else head}.",
                        "Fetch first (git fetch origin), then open the PR again.")
    merge_base = (git("merge-base", base_ref, head_ref) or "").strip()
    if not merge_base:
        raise CantJudge(f"{head} and {base} share no history in this checkout.",
                        "Fetch first (git fetch origin, or git fetch --unshallow in a shallow clone), then open the PR again.")

    def readmes(ref):
        names = git("ls-tree", "--name-only", ref)
        if names is None:
            raise CantJudge(f"git couldn't list {ref}.", "Try again once git can read the branch.")
        return [n for n in names.splitlines() if README.match(n)]

    if not readmes(head_ref):
        if readmes(merge_base):
            return refuse(f"{head} deletes the README.", f"Keep a README on {head}, updated for what changed.")
        return 0  # no README to keep current

    changed = numstat(merge_base, head_ref)
    if changed is None:
        raise CantJudge(f"git couldn't diff {head} against {base}.", "Try again once git can read both branches.")
    code = {p: n for p, n in changed.items()
            if n is not None and not README.match(p) and not NOT_CODE.search(p)}
    total = sum(code.values())
    if total < THRESHOLD:
        return 0
    touched = [p for p in changed if README.match(p)]
    if touched:
        real = numstat("-w", "--ignore-blank-lines", merge_base, head_ref, "--", *touched)
        if real is None:
            raise CantJudge(f"git couldn't diff {head}'s README.", "Try again once git can read both branches.")
        if any(real.values()):
            return 0

    biggest = sorted(code.items(), key=lambda kv: -kv[1])[:5]
    listed = ", ".join(f"{p} ({n})" for p, n in biggest)
    edit = " (its only change is whitespace)" if touched else ""
    return refuse(
        f"{head} changes {total} lines of code ({listed}) and leaves the README untouched{edit}. "
        "Updates to the README ship in the same PR as the code they describe.",
        f"Update the README on {head} for what changed (what it does, how to use it, the layout, what's next), "
        "commit it, then open the PR again.")


def run(raw):
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        if PR_CREATE_TEXT.search(raw):
            raise CantJudge("the hook's input couldn't be read.", "Try again; if it repeats, the hook needs fixing.")
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not PR_CREATE_TEXT.search(command):
        return 0

    found, parsed = resolved_commands(strip_heredoc_bodies(command))
    argvs, unreadable, remote = [], [], False
    for argv, source, on_remote in found:
        if argv is None:
            if PR_CREATE_TEXT.search(source or ""):
                unreadable.append(source)
        elif gh_subcommand_at(argv, "pr", "create"):
            argvs.append(argv)
            remote = remote or bool(on_remote)
    if not argvs and not unreadable:
        if parsed:
            return 0  # it only mentions opening a PR
        unreadable = [command]
    if unreadable:
        raise CantJudge("this command opens a PR in a way the README check can't read.",
                        "Run gh pr create on its own, as a plain command.")
    if remote:
        raise CantJudge("this command opens the PR on another machine, where the README check can't see the branch.",
                        "Run gh pr create here, in the checkout of the PR's branch.")
    if re.search(r'(?:^|[\s;&|(])GH_REPO=', command):
        raise CantJudge("this command sets GH_REPO, so the PR's repo isn't the one the README check can see.",
                        "Pass the repo with --repo, from a checkout of it.")

    enter_target_repo(payload)
    for argv in argvs:
        rc = judge(argv)
        if rc:
            return rc
    return 0


def main():
    raw = sys.stdin.read()
    try:
        return run(raw)
    except CantJudge as e:
        return refuse(f"this PR can't be judged: {e.why}", e.fix)
    except Exception as e:  # its own failure must not open the door it guards
        if PR_CREATE_TEXT.search(raw):
            return refuse(f"the README check failed ({type(e).__name__}: {e}).",
                          "Try again; if it repeats, the hook needs fixing.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
