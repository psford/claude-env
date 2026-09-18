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
    GH_FLAGS, mask_data_spans, strip_heredoc_bodies,
)

# ADJACENCY, not "these words somewhere in the line". Grace, finding 12: the
# old `\bgh\b.*\bworkflow\b.*\brun\b` and its reverse were loose enough that
# `gh run list --workflow ci.yml` -- a read -- matches both. That was tolerable
# only while a parser stood in front of them; now these run directly against
# the masked text, so the looseness would be a live false positive.
WORKFLOW_TEXT = [
    r'\bgh\s+' + GH_FLAGS + r'workflow\s+run\b',
    r'\bgh\s+' + GH_FLAGS + r'run\s+rerun\b',
    r'workflow_dispatch',
    # The REST spelling, in both orders, because the endpoint can be parked
    # in a variable and spent in a later statement:
    #     E='repos/o/r/actions/workflows/x.yml/dispatches'
    #     gh api $E -f ref=main
    # The literal then sits BEFORE `gh api`.
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

    THE SHAPE CHANGED ON 2026-09-12 (CE-13.5, Grace finding 1). This used to
    peel a list of wrappers, descend payloads, and declare the walk
    authoritative unless one of eight indirection regexes matched. Nine
    ordinary wrappers walked past it -- taskset, flock, docker run, poetry
    run, strace, chroot, runuser, script -qc, busybox sh -c -- and the list
    could never close, because nsenter, uv run, make and any script on disk
    run a command that walk would not look at. A name missing from the list
    was a SILENT PASS.

    Now the question is asked the other way round. A quoted span is treated as
    data only when the head of its statement is a command that consumes
    arguments as text -- `ticket`, `git commit -m`, `gh pr create --title` --
    and everything else leaves the span visible. The match then runs over what
    is left. A wrapper nobody has ever heard of does not hide anything,
    because hiding was never the wrapper's doing: it was the parser's.

    A name missing from the allowlist is now a refusal, which is visible and
    arguable and one line to fix, instead of a silence nobody sees.
    """
    text = mask_data_spans(strip_heredoc_bodies(command or ""))
    return any(re.search(p, text, re.IGNORECASE) for p in WORKFLOW_TEXT)


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
                "permissionDecisionReason": "BLOCKED: Claude is not permitted to trigger GitHub workflow runs. Patrick must trigger deployments manually via GitHub Actions web UI."
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
