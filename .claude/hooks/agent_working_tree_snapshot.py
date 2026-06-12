#!/usr/bin/env python3
"""
agent_working_tree_snapshot.py — PreToolUse hook for the Agent tool.

Writes `git status --porcelain` for CWD to a temp file keyed by the
session_id + a hash of the tool_input. The matching PostToolUse hook
(agent_working_tree_guard.py) reads the snapshot back and reports only
the DELTA between pre and post — eliminating the false-positive class
where the tree was already dirty going into the Agent call.

Why a hash key: the harness can run Agent tool calls in parallel and
exposes no native correlation id between Pre and Post. Hashing the
tool_input gives a deterministic key shared by the matching Pre/Post
pair for the same call. Identical inputs hashing to the same key is
benign — both calls would observe the same baseline.

Exit code is always 0 — failure to snapshot should not block the Agent
call. If the snapshot is missing, the Post hook falls back to the
old "report everything dirty" behavior, which is the safer default.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SNAP_DIR = Path("/tmp/agent-wt-snapshots")


def snapshot_path(session_id: str, tool_input: dict) -> Path:
    """Deterministic per-call snapshot path. Pre and Post both compute the same key."""
    SNAP_DIR.mkdir(exist_ok=True)
    blob = json.dumps(tool_input, sort_keys=True, default=str)
    key = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
    sid = (session_id or "nosession").replace("/", "_")[:32]
    return SNAP_DIR / f"{sid}-{key}.txt"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    session_id = payload.get("session_id") or ""

    cwd = str(Path.cwd())

    # Skip silently if CWD isn't a git repo (no snapshot needed).
    try:
        rc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        ).returncode
    except Exception:
        return
    if rc != 0:
        return

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
    except Exception:
        return
    if result.returncode != 0:
        return

    try:
        path = snapshot_path(session_id, tool_input)
        # Prefix the snapshot with the CWD so the Post hook can verify it ran
        # in the same repo (avoids weird cross-repo false positives).
        header = f"#cwd={cwd}\n"
        path.write_text(header + result.stdout, encoding="utf-8")
    except Exception:
        # Snapshot write failed; Post will fall back to full-tree reporting.
        return


if __name__ == "__main__":
    main()
