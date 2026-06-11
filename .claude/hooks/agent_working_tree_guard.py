#!/usr/bin/env python3
"""
agent_working_tree_guard.py — PostToolUse hook for the Agent tool.

After every subagent dispatch, inspect git status in CWD. If the working
tree has uncommitted changes, inject a system-reminder telling the
orchestrator (main-loop Claude) to verify those changes were disclosed
in the agent's report.

Why: across the visual-design phases (PR #16, #17), dispatched subagents
silently modified files outside their stated scope and reported
"completed" without disclosing the uncommitted edits. The orchestrator
catching it was luck, not design. This hook structurally enforces the
disclosure contract.

Performance: 2 `git` subprocess calls (rev-parse + status --porcelain)
in CWD. ~50-100ms on a normal repo. Subagent calls are not so frequent
that this matters.

Input: PostToolUse JSON payload on stdin. We don't read anything from
it — the matcher already confirmed an Agent call just finished.

Output: JSON on stdout with `hookSpecificOutput.additionalContext` when
the tree is dirty. Empty stdout when clean (silent pass).

Exit code is always 0 — failure to check should not block subsequent
hooks or tools.
"""
import json
import subprocess
import sys
from pathlib import Path

# Paths that count as session-internal noise (not agent-edited application
# state). If these are the ONLY dirty paths, suppress the reminder.
NOISE_PREFIXES = (
    ".claude/settings.local.json",
    "test-results/",
    "venv/",
    "node_modules/",
    ".pytest_cache/",
    "__pycache__/",
    ".astro/",
    "dist/",
    ".wrangler/",
)


def run(args, cwd):
    """Run a subprocess, swallow errors, return (rc, stdout)."""
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return -1, ""


def main():
    # Drain stdin (don't crash on bad payload).
    try:
        sys.stdin.read()
    except Exception:
        pass

    cwd = str(Path.cwd())

    # Skip silently if CWD isn't a git repo.
    rc, _ = run(["git", "rev-parse", "--git-dir"], cwd)
    if rc != 0:
        return

    # `git status --porcelain` is the fastest machine-readable status.
    rc, status = run(["git", "status", "--porcelain"], cwd)
    if rc != 0:
        return

    lines = [ln for ln in status.splitlines() if ln.strip()]
    if not lines:
        return  # Clean tree. Nothing to report.

    # Filter noise.
    real = []
    for line in lines:
        # Porcelain format: XY then space then path. Strip status code + space.
        path = line[3:].strip().strip('"')
        if any(path.startswith(p) for p in NOISE_PREFIXES):
            continue
        real.append(line)

    if not real:
        return  # Only noise.

    cap = 20
    body = "\n".join(real[:cap])
    if len(real) > cap:
        body += f"\n... and {len(real) - cap} more"

    reminder = (
        f"SUBAGENT POST-CALL WORKING-TREE CHECK ({cwd}):\n"
        "the subagent left uncommitted changes. Verify the agent's report "
        "EXPLICITLY disclosed each of these modifications. If it did not, the "
        "report is incomplete — address each change (commit, revert, or "
        "explicitly acknowledge) BEFORE proceeding.\n\n"
        f"git status --porcelain:\n{body}"
    )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reminder,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
