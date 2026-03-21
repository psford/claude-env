#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Guard deployment operations.

Enforces CLAUDE.md rules:
- NEVER deploy without Patrick saying "deploy"
- Must complete pre-deploy checklist
- HARD BLOCK: Claude cannot trigger GitHub workflow runs

This hook adds context for any Azure/deployment-related commands.
"""

import json
import sys
import re

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # HARD BLOCK: gh workflow run commands - Claude must NEVER trigger these
    workflow_patterns = [
        r'\bgh\b.*\bworkflow\b.*\brun\b',
        r'\bgh\b.*\brun\b.*\bworkflow\b',
        r'workflow_dispatch',
    ]

    is_workflow_trigger = any(re.search(p, command, re.IGNORECASE) for p in workflow_patterns)

    if is_workflow_trigger:
        # DENY - hard block, no bypass possible
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "reason": "BLOCKED: Claude is not permitted to trigger GitHub workflow runs. Patrick must trigger deployments manually via GitHub Actions web UI."
            }
        }
        print(json.dumps(output))
        return 0

    # Check for other deployment-related commands (prompt, don't block)
    deploy_patterns = [
        r'\baz\b.*\bwebapp\b.*\bdeploy\b',
        r'\baz\b.*\bcontainer\b.*\bcreate\b',
        r'Deploy.*Azure',
        r'deploy.*production',
    ]

    is_deploy = any(re.search(p, command, re.IGNORECASE) for p in deploy_patterns)

    if not is_deploy:
        return 0

    # This looks like a deployment - add strong reminder
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "additionalContext": """
DEPLOYMENT GUARD (from CLAUDE.md):

This looks like a production deployment command.

HARD STOP: Did Patrick explicitly say "deploy"?

Pre-deploy checklist:
1. ✅ Bicep file reviewed by Patrick?
2. ✅ TECHNICAL_SPEC.md updated?
3. ✅ FUNCTIONAL_SPEC.md updated (if user-facing)?
4. ✅ Docs updated?
5. ✅ Security scans passed?
6. ✅ User tested on localhost and approved?

If ANY checklist item is missing, STOP and complete it first.
"""
        }
    }

    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
