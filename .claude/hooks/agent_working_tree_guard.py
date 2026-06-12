#!/usr/bin/env python3
"""
agent_working_tree_guard.py — PostToolUse hook for the Agent tool.

After every subagent dispatch, inspect git status in CWD. If the working
tree has uncommitted changes THAT THE AGENT CREATED (i.e. NOT present
before the call), inject a system-reminder telling the orchestrator to
verify those changes were disclosed in the agent's report.

Delta-only design: the matching PreToolUse hook (agent_working_tree_
snapshot.py) writes pre-call `git status --porcelain` to a snapshot
file keyed by session_id + tool_input hash. This Post hook reads the
snapshot, subtracts pre-call lines from post-call lines, and reports
only the delta. Eliminates the false-positive class where the tree
was already dirty going INTO the Agent call — which is exactly the
class that Patrick called out on 2026-06-11 when I tried to override
the hook by writing "false positive, continuing."

If the snapshot is missing (e.g. Pre hook didn't run, or wrote to a
different cwd), fall back to the old "report everything dirty"
behavior — the safer default for a missing baseline.

Performance: still ~50-100ms (added one Path.read_text + set diff).

Input: PostToolUse JSON payload on stdin. We read tool_input + session_id
to compute the same snapshot key as the Pre hook.

Output: JSON on stdout with `hookSpecificOutput.additionalContext` when
the delta is non-empty. Empty stdout when clean or delta is noise-only.

Exit code is always 0 — failure to check should not block subsequent
hooks or tools.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SNAP_DIR = Path("/tmp/agent-wt-snapshots")

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


def snapshot_path_for(session_id: str, tool_input: dict) -> Path:
    """Mirror of agent_working_tree_snapshot.py — same key for the same call."""
    blob = json.dumps(tool_input, sort_keys=True, default=str)
    key = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
    sid = (session_id or "nosession").replace("/", "_")[:32]
    return SNAP_DIR / f"{sid}-{key}.txt"


def load_snapshot(path: Path, cwd: str):
    """Return (matched_cwd, set_of_status_lines) or (False, None) if missing/mismatched."""
    if not path.exists():
        return False, None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False, None
    snap_cwd = None
    lines = []
    for ln in text.splitlines():
        if ln.startswith("#cwd="):
            snap_cwd = ln[len("#cwd="):].strip()
            continue
        if ln.strip():
            lines.append(ln)
    if snap_cwd != cwd:
        return False, None
    return True, set(lines)


def main():
    # Read payload — we need tool_input + session_id to find the snapshot.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    session_id = payload.get("session_id") or ""

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

    # Load pre-call snapshot. If present and cwd matches, subtract pre-lines
    # from post-lines so we only report what the AGENT changed. If missing,
    # fall back to full-tree reporting (safer default for an absent baseline).
    snap_path = snapshot_path_for(session_id, tool_input)
    snap_ok, snap_lines = load_snapshot(snap_path, cwd)
    # Best-effort cleanup so the /tmp dir doesn't accumulate forever.
    try:
        snap_path.unlink(missing_ok=True)
    except Exception:
        pass

    if snap_ok:
        delta = [ln for ln in lines if ln not in snap_lines]
    else:
        delta = lines  # No baseline — report everything (old behavior).

    if not delta:
        return  # Nothing new since pre-call. Silent pass.

    # Filter noise (now applied AFTER delta — pre-existing noise was already
    # filtered out by the delta, but this still catches agent-created noise).
    real = []
    for line in delta:
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

    baseline_note = (
        "" if snap_ok
        else "\n(NOTE: pre-call snapshot was missing — reporting all dirty paths, "
             "not just the delta. Some of these may have existed before the agent ran.)"
    )

    reminder = (
        f"SUBAGENT POST-CALL WORKING-TREE CHECK ({cwd}):\n"
        "the subagent created uncommitted changes (delta vs. pre-call snapshot). "
        "Verify the agent's report EXPLICITLY disclosed each of these modifications. "
        "If it did not, the report is incomplete — address each change (commit, "
        "revert, or explicitly acknowledge) BEFORE proceeding."
        f"{baseline_note}\n\n"
        f"new since pre-call:\n{body}"
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
