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
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    dispatches_a_workflow, resolved_commands, strip_heredoc_bodies,
)

WORKFLOW_TEXT = [
    r'\bgh\b.*\bworkflow\b.*\brun\b',
    r'\bgh\b.*\brun\b.*\bworkflow\b',
    r'workflow_dispatch',
    # The REST spelling, in both orders, because the endpoint can be parked
    # in a variable and spent in a later statement:
    #     E='repos/o/r/actions/workflows/x.yml/dispatches'
    #     gh api $E -f ref=main
    # The literal then sits BEFORE `gh api`. This list is only consulted when
    # the token walk is not authoritative, which is exactly when the endpoint
    # is hidden behind an expansion the walk cannot resolve.
    r'\bgh\s+api\b[\s\S]*?(?:dispatches|/rerun\b)',
    r'(?:dispatches|/rerun\b)[\s\S]*?\bgh\s+api\b',
]


def _triggers_a_workflow(command):
    """True when this command actually starts a workflow run.

    Token- and position-based: a quoted argument that merely says the words --
    a ticket description, a commit message, a CSO's evidence -- is data, and
    data does not spend anybody's Actions minutes.

    The first version of this read argv0 only, and the CSO gate caught the
    price on 2026-09-11: `timeout 900 gh workflow run ios.yml` and
    `ssh build-box gh workflow run ...` both passed SILENTLY where the raw-text
    match they replaced had denied them. Narrowing a guard onto the act is only
    a fix if the act is still seen through whatever is in front of it, so the
    wrapper walk and payload descent are shared with ci_cost_guard rather than
    written a second time here.

    Unparseable input falls back to the raw match rather than to silence: a
    command this cannot read is not a command it may approve.
    """
    found, parsed = resolved_commands(strip_heredoc_bodies(command or ""))
    for argv, source, _remote in found:
        if argv is None:
            # Source, not shell. Same fail-closed raw match the whole command
            # would get, applied to the payload.
            if any(re.search(p, source, re.IGNORECASE) for p in WORKFLOW_TEXT):
                return True
            continue
        if dispatches_a_workflow(argv):
            return True
    if not parsed:
        return any(re.search(p, command, re.IGNORECASE) for p in WORKFLOW_TEXT)
    return False


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

    # HARD BLOCK: gh workflow run commands - Claude must NEVER trigger these.
    #
    # Read as TOKENS, not as text. This matched the raw string until 2026-09-11,
    # so it fired on any command that MENTIONED a dispatch -- and the thing that
    # mentions dispatches most is the evidence describing the guard that stops
    # them. The CSO gate for this repo could not record a verdict about
    # ci_cost_guard, because its evidence necessarily quotes `gh workflow run`
    # and `workflow_dispatch`. A hard deny with no bypass, deadlocking the one
    # role whose job is to say whether the repo may ship.
    #
    # ci_cost_guard had this identical defect and fixed it at CE-2.8: "a guard
    # that fires on the mention of a thing rather than on the thing costs trust,
    # which is the currency it needs to keep working." Its sibling in the same
    # directory never got the fix, which is the audit-the-class rule failing.
    #
    # Unparseable input falls back to the raw match rather than to silence: a
    # command this cannot read is not a command it may approve.
    is_workflow_trigger = _triggers_a_workflow(command)

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
    checklist = """
DEPLOYMENT GUARD (from CLAUDE.md):

This looks like a production deployment command.

HARD STOP: Did Patrick explicitly say "deploy"?

Pre-deploy checklist:
1. ✅ Bicep file reviewed by Patrick?"""

    # Only include spec checks if they exist in this repo
    if os.path.exists("projects/stock-analyzer/docs/TECHNICAL_SPEC.md"):
        checklist += "\n2. ✅ TECHNICAL_SPEC.md updated?"
        checklist += "\n3. ✅ FUNCTIONAL_SPEC.md updated (if user-facing)?"
        checklist += "\n4. ✅ Docs updated?"
        checklist += "\n5. ✅ Security scans passed?"
        checklist += "\n6. ✅ User tested on localhost and approved?"
    else:
        checklist += "\n2. ✅ Docs updated?"
        checklist += "\n3. ✅ Security scans passed?"
        checklist += "\n4. ✅ User tested on localhost and approved?"

    checklist += "\n\nIf ANY checklist item is missing, STOP and complete it first."

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "additionalContext": checklist
        }
    }

    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
