#!/usr/bin/env python3
"""
Pre-commit hook: Block direct commits to main branch.

Rule from CLAUDE.md:
- NEVER commit directly to main - PRs only, no exceptions
- main branch is sacred - production code requires formal process

This hook BLOCKS commits to main. No bypass except --no-verify.
"""

import subprocess
import sys

def get_current_branch():
    """Get the current git branch name."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def main():
    branch = get_current_branch()

    if branch == 'main':
        print("\n" + "=" * 60)
        print("ERROR: Direct commits to 'main' are BLOCKED")
        print("=" * 60)
        print("""
The main branch is protected. All changes must go through PRs.

Correct workflow:
  1. git checkout develop
  2. Make your changes
  3. git commit -m "Your message"
  4. gh pr create --base main --head develop

If you're absolutely certain you need to bypass this:
  git commit --no-verify

But this should NEVER happen in normal workflow.
""")
        print("=" * 60 + "\n")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
