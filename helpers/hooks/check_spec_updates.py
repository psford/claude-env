#!/usr/bin/env python3
"""
Pre-commit hook: Check that spec files are updated when code changes.

Rule from CLAUDE.md:
- TECHNICAL_SPEC.md must be updated for ANY code changes
- FUNCTIONAL_SPEC.md must be updated for user-facing changes

This hook warns (doesn't block) when code files are staged but specs aren't.
"""

import subprocess
import sys
from pathlib import Path

# File patterns that require TECHNICAL_SPEC.md updates
CODE_PATTERNS = {
    '.cs', '.razor', '.cshtml',  # C#
    '.py',  # Python
    '.ts', '.tsx', '.js', '.jsx',  # TypeScript/JavaScript
    '.sql',  # Database
    '.bicep', '.json',  # Infrastructure (if in infrastructure/)
}

# File patterns that require FUNCTIONAL_SPEC.md updates (user-facing)
UI_PATTERNS = {
    '.html', '.razor', '.cshtml',
    '.css', '.scss',
}

# Paths to exclude from checks
EXCLUDE_PATHS = {
    'helpers/hooks/',  # Don't require spec updates for hook changes
    'tests/',
    '.github/',
    '__pycache__/',
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

    # Categorize staged files
    code_files = []
    ui_files = []
    has_technical_spec = False
    has_functional_spec = False

    for f in staged:
        if is_excluded(f):
            continue

        path = Path(f)
        suffix = path.suffix.lower()

        if 'TECHNICAL_SPEC.md' in f:
            has_technical_spec = True
        if 'FUNCTIONAL_SPEC.md' in f:
            has_functional_spec = True

        if suffix in CODE_PATTERNS:
            code_files.append(f)
        if suffix in UI_PATTERNS:
            ui_files.append(f)

    warnings = []

    # Check for missing TECHNICAL_SPEC.md
    if code_files and not has_technical_spec:
        warnings.append(
            f"\n  WARNING: {len(code_files)} code file(s) staged but TECHNICAL_SPEC.md not updated.\n"
            f"  Code files: {', '.join(code_files[:5])}{'...' if len(code_files) > 5 else ''}\n"
            f"  Rule: Update TECHNICAL_SPEC.md for ANY code changes.\n"
        )

    # Check for missing FUNCTIONAL_SPEC.md (UI changes only)
    if ui_files and not has_functional_spec:
        warnings.append(
            f"\n  NOTE: {len(ui_files)} UI file(s) staged but FUNCTIONAL_SPEC.md not updated.\n"
            f"  UI files: {', '.join(ui_files[:5])}{'...' if len(ui_files) > 5 else ''}\n"
            f"  Rule: Update FUNCTIONAL_SPEC.md for user-facing changes (if applicable).\n"
        )

    if warnings:
        print("\n" + "=" * 60)
        print("SPEC UPDATE REMINDER")
        print("=" * 60)
        for w in warnings:
            print(w)
        print("To skip this check: git commit --no-verify")
        print("=" * 60 + "\n")

        # Return 0 to warn but not block - change to 1 to enforce
        return 0

    return 0

if __name__ == '__main__':
    sys.exit(main())
