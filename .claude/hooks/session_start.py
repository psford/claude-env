#!/usr/bin/env python3
"""
Claude Code SessionStart hook: Load critical context at session start.

Outputs a reminder of critical checkpoints that Claude should always follow.
This text is added to Claude's context at the start of every session.
"""

import json
import sys

def main():
    # Output plain text that will be added to Claude's context
    print("""
=== CRITICAL CHECKPOINTS (enforced by hooks) ===

COMMITS: Show status -> diff -> log -> message -> WAIT for explicit approval
MAIN BRANCH: Never commit, merge, push --force, or rebase on main
REVERSE MERGE: Never merge main INTO develop (flow is develop -> main)
PR MERGE: Patrick merges via GitHub web only - never use `gh pr merge`
DEPLOY: Only when Patrick says "deploy" + pre-deploy checklist complete
SPECS: Update TECHNICAL_SPEC.md AS you code, stage with code
QUESTIONS: If user asks a question, answer and wait - not implicit approval

These rules are enforced by Claude Code hooks. Violations will be blocked.
""")
    return 0

if __name__ == "__main__":
    sys.exit(main())
