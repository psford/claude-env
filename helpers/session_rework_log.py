#!/usr/bin/env python3
"""
session_rework_log.py — capture abandoned approaches so pre-commit thrashing
isn't invisible to future retros (it leaves no trace in clean git history).

Background: 2026-06-26 single-screen overview — ~2h of failed emphasis mechanisms
were tried and reverted before any commit. The git log shows none of it.

Two modes:

1. Manual (preferred — zero false positives):
     python helpers/session_rework_log.py --log \
       --file src/site/overview-fit.ts \
       --approach "row-height multiplier for emphasis" \
       --why "fitToHeight re-solves the base height and neutralizes it" \
       --measured "identical layouts with/without the flag at 2560x1440"
   Appends a timestamped entry to .claude/session-rework.md (gitignored, local).

2. Advisory hook (PostToolUse Write, exit 0): counts writes per file this session;
   once a file passes the threshold, emits an advisory nudging a --log entry.
   WEAK signal (high false-positive on busy files) — never blocks.

Pass a timestamp via --now (ISO) for determinism in tests; defaults to wall clock.
"""

import argparse
import json
import os
import sys

REWORK_LOG = ".claude/session-rework.md"
WRITE_COUNTS = ".claude/.session-write-counts.json"
WRITE_THRESHOLD = 5


def log_entry(file, approach, why, measured, now):
    os.makedirs(".claude", exist_ok=True)
    entry = (
        f"\n## {now} — abandoned approach in `{file}`\n\n"
        f"**Approach:** {approach}\n\n**Why it failed:** {why}\n\n"
        f"**Measured/observed:** {measured}\n\n---\n"
    )
    existing = ""
    if os.path.exists(REWORK_LOG):
        with open(REWORK_LOG, encoding="utf-8") as f:
            existing = f.read()
    if not existing:
        existing = (
            "# Session Rework Log\n\nLocal-only record of abandoned approaches "
            "(not committed). Add `.claude/session-rework.md` to .gitignore.\n"
        )
    with open(REWORK_LOG, "w", encoding="utf-8") as f:
        f.write(existing.rstrip() + "\n" + entry)
    print(f"[session_rework_log] appended to {REWORK_LOG}")


def hook_mode():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Write":
        return 0
    path = data.get("tool_input", {}).get("file_path", "")
    if not path:
        return 0
    counts = {}
    if os.path.exists(WRITE_COUNTS):
        try:
            with open(WRITE_COUNTS, encoding="utf-8") as f:
                counts = json.load(f)
        except Exception:
            counts = {}
    counts[path] = counts.get(path, 0) + 1
    os.makedirs(".claude", exist_ok=True)
    with open(WRITE_COUNTS, "w", encoding="utf-8") as f:
        json.dump(counts, f)
    if counts[path] < WRITE_THRESHOLD:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[session_rework_log] {path} written {counts[path]}x this session. "
                "If you're cycling approaches, log the abandoned one: "
                "python helpers/session_rework_log.py --log --file ... --approach ... "
                "--why ... --measured ...  (advisory; weak signal)."
            ),
        }
    }))
    return 0


def main():
    if "--log" in sys.argv:
        p = argparse.ArgumentParser()
        p.add_argument("--log", action="store_true")
        p.add_argument("--file", required=True)
        p.add_argument("--approach", required=True)
        p.add_argument("--why", required=True)
        p.add_argument("--measured", default="(not recorded)")
        p.add_argument("--now", default=None)
        a = p.parse_args()
        now = a.now
        if not now:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        log_entry(a.file, a.approach, a.why, a.measured, now)
        return 0
    return hook_mode()


if __name__ == "__main__":
    sys.exit(main())
