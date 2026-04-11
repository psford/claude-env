#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: Cross-repo fix audit.

Fires AFTER git commit when the commit message starts with "fix:" or "fix!:"
and committed files match infrastructure patterns. Injects advisory context
naming companion repos that should be audited for the same issue.

This hook helps prevent fixes from being applied in only one place when
the pattern exists across the infrastructure codebase.

Hook event: PostToolUse (fires AFTER tool completes)
Matcher: Bash (only git commit commands)
Exit code: Always 0 (advisory, not blocking)
"""

import json
import os
import re
import subprocess
import sys


# Infrastructure file patterns to watch
INFRA_PATTERNS = [
    r"\.bicep$",
    r"infrastructure/azure/",
    r"\.github/workflows/",
    r"Dockerfile",
    r"appsettings\.Production\.json",
    r"roleAssignment",
    r"principalId",
    r"Microsoft\.Authorization",
    r"Microsoft\.KeyVault",
    r"KeyVault",
]

# Companion repo paths
COMPANION_REPOS = [
    "/home/patrick/projects/road-trip",
    "/home/patrick/projects/stock-analyzer",
]


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git commit" not in command:
        return 0

    # Get last commit message
    commit_msg = get_last_commit_message()
    if not commit_msg:
        return 0

    # Only trigger on fix: or fix!: prefix
    if not re.match(r"^fix[!:]", commit_msg):
        return 0

    # Get committed files
    committed_files = get_committed_files()
    if not committed_files:
        return 0

    # Check if any files match infra patterns
    infra_matches = filter_infra_files(committed_files)
    if not infra_matches:
        return 0

    # If we get here: fix commit with infra files involved
    # Inject advisory context
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": generate_audit_context(commit_msg, infra_matches)
        }
    }
    print(json.dumps(output))
    return 0


def get_last_commit_message():
    """Get the subject line of the most recent commit."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_committed_files():
    """Get list of files changed in the last commit."""
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return []
    except Exception:
        return []


def filter_infra_files(files):
    """Filter files that match infrastructure patterns."""
    matches = []
    for filepath in files:
        for pattern in INFRA_PATTERNS:
            if re.search(pattern, filepath):
                matches.append(filepath)
                break
    return matches


def generate_audit_context(commit_msg, infra_files):
    """Generate audit advisory text."""
    repos_list = "\n".join(f"  - {repo}" for repo in COMPANION_REPOS)
    files_list = "\n".join(f"  - {f}" for f in infra_files[:5])
    if len(infra_files) > 5:
        files_list += f"\n  - ... and {len(infra_files) - 5} more"

    return f"""
⚠️ INFRASTRUCTURE FIX — CROSS-REPO AUDIT RECOMMENDED ⚠️

Commit: {commit_msg}

Files changed:
{files_list}

Since infrastructure patterns are involved, check if the same issue exists in companion repos:
{repos_list}

Steps to audit:
1. Review the fix in the context of your infrastructure architecture
2. Search companion repos for similar patterns: `git log --all --grep="fix" -- {infra_files[0]}`
3. If the pattern exists elsewhere, apply the same fix consistently

This is NOT a blocking check — just a reminder to prevent infrastructure divergence.
"""


if __name__ == "__main__":
    sys.exit(main())
