#!/usr/bin/env python3
"""
Pre-commit hook: Validate markdown links in documentation.

Rule from CLAUDE.md:
- Before committing documentation changes, verify all markdown links resolve.
- Broken links are unacceptable.

This hook runs check_links.py when markdown files are staged.
"""

import subprocess
import sys
from pathlib import Path

def get_staged_files():
    """Get list of staged files."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []

def main():
    staged = get_staged_files()
    if not staged:
        return 0

    # Check if any markdown files are staged
    md_files = [f for f in staged if f.lower().endswith('.md')]

    if not md_files:
        return 0

    print(f"\nValidating links in {len(md_files)} markdown file(s)...")

    # Find check_links.py
    script_dir = Path(__file__).parent.parent
    check_links = script_dir / 'check_links.py'

    if not check_links.exists():
        print(f"  Warning: {check_links} not found, skipping link validation")
        return 0

    # Run check_links.py on each staged markdown file
    failed = False
    for md_file in md_files:
        result = subprocess.run(
            [sys.executable, str(check_links), md_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"\n  BROKEN LINKS in {md_file}:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            failed = True

    if failed:
        print("\n" + "=" * 60)
        print("ERROR: Broken links detected in documentation")
        print("=" * 60)
        print("Fix the broken links before committing.")
        print("To skip this check: git commit --no-verify")
        print("=" * 60 + "\n")
        return 1

    print("  All links valid.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
