#!/usr/bin/env python3
"""
regression_test_red_verify.py — pre-push verification of `RED: <sha>` claims.

For each commit being pushed whose changes are entirely vitest test files
(*.test.ts / *.test.tsx), require a `RED: <sha>` line in the commit message
and verify the test FAILS when applied against that sha's tree.

Why: tests that pass shape-checks but don't catch their named bug are the
worst-class regression we've shipped (PR #16 cycle-2 + PR #17 AC2.8). The
test claims "AC1.5 verifies feed order" but the body only asserts an
<article> exists. Mechanical verification: "the test you wrote DID fail
on the broken state" is the proof the test catches what its name claims.

Convention:
  RED: <full-or-short-sha>   — verify test fails on this sha's tree
  RED: HEAD~1                — verify against the immediate parent
  RED: none                  — explicit opt-out (greenfield TDD; nothing broken yet)

Scope:
  - vitest only for MVP. Playwright (*.spec.ts) is skipped — would need a
    wrangler-dev spin-up per verification, dramatically heavier. Layer in
    after the vitest pattern proves itself.
  - Only test-only commits (no impl files in the diff). Mixed commits
    can't be verified the same way and need a different strategy.

Inputs (git pre-push format on stdin):
  <local_ref> <local_sha> <remote_ref> <remote_sha>\n  (one per ref)

Exit codes:
  0 — verification passed (all RED claims true)
  1 — verification failed (block push)
  2 — internal error (block push to be safe)

Bypass: `git push --no-verify` (standard git escape).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RED_LINE = re.compile(r"^\s*RED:\s*(\S+)\s*$", re.MULTILINE)
VITEST_FILE = re.compile(r"\.test\.(ts|tsx|js|jsx)$")
PLAYWRIGHT_FILE = re.compile(r"\.spec\.(ts|tsx|js|jsx)$")
ZERO_SHA = "0000000000000000000000000000000000000000"


def git(*args, cwd=None, check=True, capture=True):
    """Run a git command. Return stdout (or raise on non-zero if check=True)."""
    return subprocess.run(
        ["git", *args],
        capture_output=capture,
        text=True,
        cwd=cwd,
        check=check,
    ).stdout


def files_in_commit(sha, repo_root):
    """List files modified in a commit (paths relative to repo root)."""
    out = git("diff-tree", "--no-commit-id", "--name-only", "-r", sha, cwd=repo_root)
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_test_only_commit(files):
    """True iff every modified file is a vitest test file."""
    if not files:
        return False
    for f in files:
        if not VITEST_FILE.search(f):
            return False
    return True


def has_playwright_files(files):
    return any(PLAYWRIGHT_FILE.search(f) for f in files)


def parse_red(message):
    """Extract the first RED: value from the commit message, or None."""
    m = RED_LINE.search(message)
    return m.group(1) if m else None


def resolve_sha(ref, repo_root):
    """Resolve a ref (full sha, short sha, HEAD~N) to a full sha."""
    try:
        return git("rev-parse", "--verify", ref, cwd=repo_root).strip()
    except subprocess.CalledProcessError:
        return None


def verify_red(commit_sha, red_sha, test_files, repo_root):
    """
    Verify that running each test file in worktree-at-red_sha produces a
    non-zero exit. Returns (ok, message).
    """
    worktree = tempfile.mkdtemp(prefix="red-verify-")
    try:
        try:
            git("worktree", "add", "--detach", worktree, red_sha, cwd=repo_root)
        except subprocess.CalledProcessError as e:
            return False, f"git worktree add failed: {e.stderr or e.stdout}"

        # Symlink node_modules from main repo to avoid full re-install.
        main_node_modules = Path(repo_root) / "node_modules"
        worktree_node_modules = Path(worktree) / "node_modules"
        if main_node_modules.exists() and not worktree_node_modules.exists():
            try:
                worktree_node_modules.symlink_to(main_node_modules)
            except OSError:
                pass  # Fall through to npm install if needed

        # Apply each test file from the to-push commit onto the worktree.
        for tf in test_files:
            content = subprocess.run(
                ["git", "show", f"{commit_sha}:{tf}"],
                capture_output=True, text=True, cwd=repo_root,
                check=False,
            )
            if content.returncode != 0:
                return False, f"cannot read {tf} from commit {commit_sha}"
            dest = Path(worktree) / tf
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content.stdout)

        # Run vitest on the test files. Expect non-zero exit.
        result = subprocess.run(
            ["npx", "vitest", "run", "--reporter=basic", *test_files],
            capture_output=True, text=True, cwd=worktree,
            timeout=120,
        )
        if result.returncode == 0:
            # Test PASSED on the broken state — the test doesn't catch the bug.
            short_red = red_sha[:8]
            short_commit = commit_sha[:8]
            tail = result.stdout.splitlines()[-10:]
            return False, (
                f"\n  Commit {short_commit} claims RED: {short_red} but the "
                f"test PASSED on that sha's tree.\n"
                f"  This means the test does not actually catch what its "
                f"name claims. Either:\n"
                f"    (a) fix the test so it fails on the broken state, or\n"
                f"    (b) point RED: at a different sha where the bug exists, or\n"
                f"    (c) use `RED: none` if this is greenfield (no broken state in history).\n"
                f"  Test output tail:\n    " + "\n    ".join(tail)
            )
        return True, f"verified red on {red_sha[:8]} (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, f"vitest timed out on {red_sha[:8]}"
    finally:
        try:
            git("worktree", "remove", "--force", worktree, cwd=repo_root, check=False)
        except Exception:
            pass
        shutil.rmtree(worktree, ignore_errors=True)


def commits_in_range(remote_sha, local_sha, repo_root):
    """List commit shas being pushed (oldest first).

    For a known remote_sha: commits in remote_sha..local_sha.
    For a new branch (remote_sha=zero): commits in local_sha not on any
    remote — `--not --remotes`. This avoids scanning the entire branch
    history back to the root commit, which would re-check commits that
    are already on main and would (legitimately) lack the RED: convention
    if they predate it.
    """
    try:
        if remote_sha == ZERO_SHA:
            out = git("rev-list", "--reverse", local_sha, "--not", "--remotes", cwd=repo_root)
        else:
            out = git("rev-list", "--reverse", f"{remote_sha}..{local_sha}", cwd=repo_root)
    except subprocess.CalledProcessError:
        return []
    return [s.strip() for s in out.splitlines() if s.strip()]


def commit_message(sha, repo_root):
    return git("log", "-1", "--format=%B", sha, cwd=repo_root)


def main():
    try:
        repo_root = git("rev-parse", "--show-toplevel").strip()
    except subprocess.CalledProcessError:
        # Not a git repo — pass through.
        return 0

    failures = []
    playwright_skipped = []

    for raw in sys.stdin:
        parts = raw.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA:
            continue  # branch deletion
        for commit in commits_in_range(remote_sha, local_sha, repo_root):
            files = files_in_commit(commit, repo_root)
            if not files:
                continue

            test_files = [f for f in files if VITEST_FILE.search(f)]
            playwright_files = [f for f in files if PLAYWRIGHT_FILE.search(f)]

            if playwright_files and not test_files and all(PLAYWRIGHT_FILE.search(f) for f in files):
                playwright_skipped.append((commit[:8], len(playwright_files)))
                continue

            if not is_test_only_commit(files):
                # Mixed commits (test + impl) — out of scope for MVP.
                continue

            msg = commit_message(commit, repo_root)
            red = parse_red(msg)

            if red is None:
                short = commit[:8]
                failures.append(
                    f"  Commit {short}: test-only commit but no `RED: <sha>` line.\n"
                    f"    Add `RED: HEAD~1` (typical) or `RED: <full-sha>` to the commit message,\n"
                    f"    OR `RED: none` for greenfield tests with no broken state in history.\n"
                    f"    Then `git commit --amend` and re-push."
                )
                continue

            if red.lower() == "none":
                continue  # explicit opt-out

            red_sha = resolve_sha(red, repo_root)
            if red_sha is None:
                failures.append(
                    f"  Commit {commit[:8]}: RED: {red} — cannot resolve to a sha."
                )
                continue

            ok, msg_text = verify_red(commit, red_sha, test_files, repo_root)
            if not ok:
                failures.append(f"  Commit {commit[:8]}: {msg_text}")
            else:
                print(f"[pre-push] {commit[:8]} {msg_text}")

    if playwright_skipped:
        for sha, n in playwright_skipped:
            print(f"[pre-push] {sha}: {n} Playwright test file(s) — RED verification not enforced for *.spec.* yet")

    if failures:
        print()
        print("[pre-push] BLOCKED: regression test verification failed.")
        for f in failures:
            print(f)
        print()
        print("To bypass (use sparingly): `git push --no-verify`")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"[pre-push] regression_test_red_verify.py internal error: {e}", file=sys.stderr)
        sys.exit(2)
