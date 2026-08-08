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
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _repo_context import enter_target_repo, workspace_repos  # noqa: E402

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


def load_snapshot(path: Path):
    """Parse the pre-call snapshot into {repo_path: set(status_lines)}.

    Returns None when the snapshot is missing or unreadable, which the caller
    treats as "no baseline" and reports the full tree.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    per_repo, current = {}, None
    for ln in text.splitlines():
        if ln.startswith("#repo="):
            current = ln[len("#repo="):].strip()
            per_repo.setdefault(current, set())
            continue
        if current and ln.strip():
            per_repo[current].add(ln)
    return per_repo or None


def main():
    # Read payload — we need tool_input + session_id to find the snapshot.
    try:
        payload = json.load(sys.stdin)
        enter_target_repo(payload)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    session_id = payload.get("session_id") or ""

    snap_path = snapshot_path_for(session_id, tool_input)
    snapshot = load_snapshot(snap_path)
    # Best-effort cleanup so the /tmp dir doesn't accumulate forever.
    try:
        snap_path.unlink(missing_ok=True)
    except Exception:
        pass

    # Check every repo the subagent could have touched. Watching only the
    # session's repo is why wander into a sibling was invisible: an Agent
    # payload carries no command, so there is nothing to point us at the repo
    # the subagent actually worked in.
    watched = workspace_repos(str(Path.cwd()))
    if snapshot:
        # Include repos seen pre-call even if they have since vanished from
        # discovery, so a deleted or moved checkout still gets reported.
        watched = list(dict.fromkeys(watched + list(snapshot)))

    findings = []
    for repo in watched:
        rc, status = run(["git", "status", "--porcelain"], repo)
        if rc != 0:
            continue
        lines = [ln for ln in status.splitlines() if ln.strip()]
        if not lines:
            continue

        baseline = snapshot.get(repo) if snapshot else None
        delta = [ln for ln in lines if ln not in baseline] if baseline is not None else lines

        real = []
        for line in delta:
            path = line[3:].strip().strip('"')
            if any(path.startswith(p) for p in NOISE_PREFIXES):
                continue
            real.append(line)
        if real:
            findings.append((repo, real, baseline is not None))

    if not findings:
        return  # Nothing new anywhere. Silent pass.

    cap = 20
    blocks, missing_baseline = [], False
    for repo, real, had_baseline in findings:
        missing_baseline = missing_baseline or not had_baseline
        body = "\n".join(real[:cap])
        if len(real) > cap:
            body += f"\n... and {len(real) - cap} more"
        blocks.append(f"{repo}:\n{body}")

    baseline_note = (
        "" if not missing_baseline
        else "\n(NOTE: no pre-call snapshot for at least one repo — reporting all dirty "
             "paths there, not just the delta. Some may predate the agent.)"
    )

    scope = f"{len(findings)} repo(s)" if len(findings) > 1 else findings[0][0]
    reminder = (
        f"SUBAGENT POST-CALL WORKING-TREE CHECK ({scope}):\n"
        "the subagent created uncommitted changes (delta vs. pre-call snapshot). "
        "Verify the agent's report EXPLICITLY disclosed each of these modifications. "
        "If it did not, the report is incomplete — address each change (commit, "
        "revert, or explicitly acknowledge) BEFORE proceeding."
        f"{baseline_note}\n\n"
        f"new since pre-call:\n" + "\n\n".join(blocks)
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
