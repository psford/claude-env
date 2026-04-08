#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Bicep infrastructure task guard.

Blocks plan phase file commits that reference Bicep/KeyVault/RBAC infrastructure
without a corresponding deployment task in the plan.

This prevents implementation plans from documenting infrastructure changes
without planning how they will actually be deployed.

Hook event: PreToolUse (fires BEFORE tool executes)
Matcher: Bash (only git commit commands)
Exit code: 0 (allow), 2 (block with error)
"""

import json
import os
import re
import subprocess
import sys


# Infrastructure references to detect
INFRA_REFS = [
    r"\.bicep",
    r"KeyVault",
    r"roleAssignment",
    r"RBAC",
    r"Microsoft\.Authorization",
    r"Microsoft\.KeyVault",
]

# Deployment task patterns to match
DEPLOY_TASKS = [
    r"az\s+deployment\s+group\s+create",
    r"az\s+bicep",
    r"az\s+keyvault\s+create",
    r"az\s+role\s+assignment\s+create",
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

    # Get staged files
    staged_files = get_staged_files()
    if not staged_files:
        return 0

    # Check only plan phase files
    plan_files = [f for f in staged_files if re.search(r"docs/implementation-plans/.*phase_\d+\.md$", f)]
    if not plan_files:
        return 0

    # Check each plan file
    for plan_file in plan_files:
        if not check_plan_file(plan_file):
            return 2

    return 0


def get_staged_files():
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return []
    except Exception:
        return []


def check_plan_file(filepath):
    """Check if a plan file has infra refs without deploy task. Returns True if OK, False if blocked."""
    try:
        result = subprocess.run(
            ["git", "show", f":{filepath}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return True  # Not in staged — allow
        
        content = result.stdout
        
        # Check for bypass comment
        if "<!-- INFRA-DEPLOY-OK:" in content:
            return True
        
        # Check for infra references
        has_infra_ref = any(re.search(pattern, content) for pattern in INFRA_REFS)
        if not has_infra_ref:
            return True  # No infra ref — allow
        
        # Has infra ref — check for deploy task
        has_deploy_task = any(re.search(pattern, content) for pattern in DEPLOY_TASKS)
        
        if not has_deploy_task:
            print(
                f"\n❌ BICEP INFRA TASK GUARD: {filepath}",
                file=sys.stderr
            )
            print(
                "   Plan references infrastructure (Bicep, KeyVault, RBAC) but has NO deployment task.",
                file=sys.stderr
            )
            print(
                "   Add a task with: az deployment group create, az bicep, az keyvault create, or az role assignment create",
                file=sys.stderr
            )
            print(
                "   Or bypass with: <!-- INFRA-DEPLOY-OK: reason -->",
                file=sys.stderr
            )
            return False
        
        return True
    
    except Exception:
        return True  # On error, allow


if __name__ == "__main__":
    sys.exit(main())
