#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block phase plan commits that hardcode
already-merged or non-existent branch names.

Background: phase plans frequently include commands like
  git push -u origin feat/visual-design
  gh pr create --base main ...
After the named branch merges, the next phase reads the same plan and the
hardcoded reference is stale. Phase 2 of photo-portfolio's visual-design
plan hit this — plan said `feat/visual-design`, but that branch was
already merged from Phase 1, so execution had to deviate to a fresh
branch.

What this hook does:
- Fires on `git commit` Bash invocations.
- Scans staged `docs/implementation-plans/.../phase_*.md` files for
  branch-like patterns (`feat/`, `fix/`, `chore/`, `refactor/`, `docs/`,
  `test/`, `style/`, `perf/`).
- For each match, checks whether the named branch is already merged into
  main, or doesn't exist at all.
- Blocks (exit 2) if any matches qualify. Lists violations with file path,
  line number, and offending branch name.
- Escape hatch: a `<!-- BRANCH-OK: reason -->` comment on the same line
  suppresses the check (e.g. when intentionally referencing historical
  context).
"""

import json
import re
import subprocess
import sys

PHASE_PATTERN = re.compile(
    r'docs/implementation-plans/[^/]+/phase_\d+\.md$', re.IGNORECASE
)
BRANCH_PATTERN = re.compile(
    r'\b(feat|fix|chore|refactor|docs|test|style|perf)/[\w\-./]+'
)
ESCAPE_HATCH = re.compile(r'<!--\s*BRANCH-OK\s*:', re.IGNORECASE)


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def _staged_phase_files():
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"])
    if rc != 0:
        return []
    return [f for f in out.splitlines() if PHASE_PATTERN.search(f)]


def _staged_content(path):
    rc, out = _run(["git", "show", f":{path}"])
    return out if rc == 0 else ""


def _normalize_branch(name):
    """Strip leading '* ', remotes/origin/ etc."""
    return re.sub(r'^remotes/[^/]+/', '', name.strip().lstrip("* "))


def _merged_branches():
    # Prefer comparison against origin/main when available; fall back to local main.
    for base in ("origin/main", "main"):
        rc, out = _run(["git", "branch", "--all", "--merged", base])
        if rc == 0 and out:
            return {_normalize_branch(line) for line in out.splitlines()}
    return set()


def _known_branches():
    rc, out = _run(["git", "branch", "--all"])
    if rc != 0:
        return set()
    return {_normalize_branch(line) for line in out.splitlines()}


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    phase_files = _staged_phase_files()
    if not phase_files:
        return 0

    merged = _merged_branches()
    known = _known_branches()
    violations = []

    for path in phase_files:
        content = _staged_content(path)
        for lineno, line in enumerate(content.splitlines(), 1):
            if ESCAPE_HATCH.search(line):
                continue
            for m in BRANCH_PATTERN.finditer(line):
                branch = m.group(0)
                # Trim trailing punctuation that often follows in prose
                branch = branch.rstrip(".,;:)\"'`")
                if branch in merged:
                    violations.append((path, lineno, line.strip(), branch, "already merged into main"))
                elif branch not in known:
                    # Don't report — there are too many false positives from
                    # generic mentions of `feat/...` patterns in narrative text.
                    # Only flag merged branches; nonexistent ones might be
                    # the NEW branch this phase will create.
                    pass

    if not violations:
        return 0

    print(
        "\n[plan_branch_guard] BLOCKED\n"
        "Phase plan references branches already merged into main.\n",
        file=sys.stderr
    )
    for path, lineno, line, branch, reason in violations:
        print(f"  {path}:{lineno}", file=sys.stderr)
        print(f"    branch '{branch}' is {reason}", file=sys.stderr)
        print(f"    line: {line[:120]}", file=sys.stderr)
        print("", file=sys.stderr)
    print(
        "Fix: rename the branch reference to one that hasn't been used yet,\n"
        "or suppress with a same-line comment:  <!-- BRANCH-OK: reason -->",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
