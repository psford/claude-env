#!/usr/bin/env python3
"""
Pre-commit hook: Remind about responsive testing for UI changes.

Rule from CLAUDE.md:
- For UI changes affecting layout/CSS: Run responsive tests at all three
  viewport sizes BEFORE committing
- This is MANDATORY for any HTML/CSS changes

This hook warns when HTML/CSS files are staged.
"""

import subprocess
import sys
from pathlib import Path

# File patterns that require responsive testing
UI_PATTERNS = {'.html', '.css', '.scss', '.razor', '.cshtml'}

# Paths to exclude
EXCLUDE_PATHS = {
    'wwwroot/lib/',  # Third-party libraries
    'node_modules/',
    '.github/',
}

def get_staged_files():
    """Get list of staged files."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []

def is_excluded(filepath):
    """Check if file is in an excluded path."""
    return any(excl in filepath for excl in EXCLUDE_PATHS)

def main():
    staged = get_staged_files()
    if not staged:
        return 0

    ui_files = []
    for f in staged:
        if is_excluded(f):
            continue
        path = Path(f)
        if path.suffix.lower() in UI_PATTERNS:
            ui_files.append(f)

    if ui_files:
        print("\n" + "=" * 60)
        print("RESPONSIVE TESTING REMINDER")
        print("=" * 60)
        print(f"""
You're committing {len(ui_files)} UI file(s):
  {chr(10).join('  - ' + f for f in ui_files[:10])}{'  ...' if len(ui_files) > 10 else ''}

Before committing UI changes, run responsive tests:

  python helpers/responsive_test.py http://localhost:5000/<page> --prefix <name>

This captures screenshots at:
  - Mobile (390x844) - iPhone size
  - Tablet (768x1024) - iPad portrait
  - Desktop (1400x900) - Standard laptop

Review screenshots to verify layout works at each size.
""")
        print("=" * 60 + "\n")

    return 0  # Warn only, don't block

if __name__ == '__main__':
    sys.exit(main())
