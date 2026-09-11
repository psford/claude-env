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
from _repo_context import statements, strip_heredoc_bodies  # noqa: E402,I001

WORKFLOW_TEXT = [
    r'\bgh\b.*\bworkflow\b.*\brun\b',
    r'\bgh\b.*\brun\b.*\bworkflow\b',
    r'workflow_dispatch',
]

# The flag spellings that name a repo, so `gh workflow run -R owner/repo` is
# seen for what it is wherever it points.
ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*=')


def _triggers_a_workflow(command):
    """True when this command actually starts a workflow run.

    Token- and position-based: `gh` in the command slot, then the subcommand
    that dispatches. A quoted argument that merely says the words -- a ticket
    description, a commit message, a CSO's evidence -- is data, and data does
    not spend anybody's Actions minutes.
    """
    import shlex
    parsed_any = False
    for statement in statements(strip_heredoc_bodies(command or "")):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        parsed_any = True
        while tokens and ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        if not tokens or os.path.basename(tokens[0]) != "gh":
            continue
        rest = tokens[1:]
        if rest[:2] == ["workflow", "run"] or rest[:2] == ["run", "rerun"]:
            return True
        if rest[:1] == ["api"] and any(
                "dispatches" in a or "/rerun" in a for a in rest):
            return True
    if not parsed_any:
        # Nothing readable: fail closed on the old text match rather than
        # letting an unparseable command through.
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
