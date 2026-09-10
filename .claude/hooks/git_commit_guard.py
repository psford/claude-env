#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Guard git commit operations.

Enforces CLAUDE.md rules:
- Must show status, diff, log before commit
- Must wait for explicit user approval
- Specs should be updated with code

EXCEPTION: Feature branches off develop are auto-approved.
Claude can commit freely to feature/* branches without user approval.
This enables autonomous implementation plan execution.

This hook runs BEFORE Bash commands that look like git commits.
It adds context reminding Claude of the commit protocol.
"""

import json
import sys
import re
import subprocess
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402
    commit_tokens, enter_target_repo, strip_heredoc_bodies)

def get_current_branch():
    """Current branch of the repo this hook was pointed at.

    Delegates to _repo_context, which uses `branch --show-current` -- rev-parse
    reports "HEAD" (or fails) on an unborn branch, so a brand-new repo looked
    like a detached head and never matched as a feature branch.
    """
    from _repo_context import current_branch
    return current_branch() or ""

def is_feature_branch(branch):
    """Check if branch is a feature branch off develop (not develop or main itself)."""
    if not branch or branch in ("develop", "main", "master", "HEAD"):
        return False
    # Feature branches: feature/*, fix/*, chore/*, or any branch that isn't develop/main
    # The key rule: NOT develop and NOT main = feature branch = auto-approve
    return True

def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
        enter_target_repo(hook_input)
    except json.JSONDecodeError:
        return 0  # Can't parse, let it through

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only care about Bash commands
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # A heredoc body is a document, not a command. Writing a retrospective that
    # says "never run git commit on main" is not running git commit.
    # See tests/test_prose_is_not_a_command.py, which holds this for every hook.
    command = strip_heredoc_bodies(command)

    # Is this actually a commit? CH-237.6 (Grace F3).
    #
    # This was `re.search(r'\bgit\b.*\bcommit\b')` -- the two words anywhere, in
    # that order -- and it decided far more than commits. On a feature branch it
    # returned permissionDecision "allow" for every one of these:
    #
    #     git log --grep commit
    #     git checkout -b fix/commit-gate
    #     echo "remember to git commit later"
    #     a hook payload that merely NAMES a git command
    #
    # An `allow` is an active grant that suppresses the permission prompt, so
    # the hook was approving commands it had never identified. On develop the
    # same match produced an `ask` instead, which a subagent cannot answer --
    # measured as the only hook in either repo that fired on a payload naming
    # git and commit, and the reason a dispatched Clyde could not exercise a
    # criterion about hook behaviour at all.
    #
    # commit_tokens lives in _repo_context and exists for exactly this. Its
    # docstring names the sibling bug: "On 2026-08-08 exactly that pattern
    # blocked the creation of a branch whose name contained 'commit'."
    #
    # Not narrowed further than that. The feature-branch allow below is a
    # deliberate, tested exemption -- the per-commit bottleneck Patrick removed
    # on purpose -- and it stays.
    if commit_tokens(command) is None:
        return 0

    # Check current branch - feature branches get auto-approved
    branch = get_current_branch()
    if is_feature_branch(branch):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": f"Auto-approved: commit on feature branch '{branch}'"
            }
        }
        print(json.dumps(output))
        return 0

    # On develop or main - full commit protocol required
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",  # Always ask for commits on develop/main
            "additionalContext": """
COMMIT PROTOCOL REMINDER (from CLAUDE.md):

Before this commit executes, verify:
1. Did you show `git status` to the user?
2. Did you show `git diff` to the user?
3. Did you show `git log -3` for message style?
4. Did you propose a commit message?
5. Did you put the checkpoint ON THE BOARD, not only in chat?
6. Did the user give EXPLICIT approval ("ok", "commit", "go ahead")?

CE-2.4. Step 5 is the one that keeps getting skipped, and skipping it is
invisible: the prompt appears in chat, Patrick's queue says "Nothing is
waiting on you", and the checkpoint sits somewhere he is not looking. He
has said he no longer reads the transcript for questions.

  ticket ask <ID> --question "OK to commit? <message subject>" \
    --audience patrick \
    --context "$(git status --short; echo; git diff --stat)"

Both surfaces are valid and whichever answer arrives first proceeds, so
this costs nothing when he is already reading chat. Skip it only when the
repo has no ticket store to hang the question on.

If ANY of these are missing, STOP and complete them first.
A question from the user is NOT approval - answer it and wait again.
Note: Spec updates are checked at push time by spec_staleness_guard.py, not per-commit.
"""
        }
    }

    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
