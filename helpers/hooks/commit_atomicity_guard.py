#!/usr/bin/env python3
"""
Pre-commit hook: Block oversized commits and warn on mixed-concern commits.

Rules from CLAUDE.md:
- Commits should be small and focused (no more than 20 files)
- Prod and test changes should be in separate commits where practical
- C# and Python changes in the same commit signal mixed concerns

This hook BLOCKS commits with more than 20 staged files.
It WARNS (but allows) commits mixing prod+test or C#+Python files.
"""

import subprocess
import sys

MAX_FILES = 20


def get_staged_files() -> list[str]:
    """Return list of staged file paths (added, copied, modified, renamed)."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().splitlines()
    return [line for line in lines if line]


def classify_files(files: list[str]) -> dict:
    """
    Classify staged files into concern buckets.

    Returns a dict with keys:
        prod_cs  -- .cs files NOT in tests/ or Tests/ directories
        test_cs  -- .cs files IN tests/ or Tests/ directories
        prod_py  -- .py files NOT in tests/ directories
        test_py  -- .py files IN tests/ directories
        other    -- everything else
    """
    classified: dict[str, list[str]] = {
        'prod_cs': [],
        'test_cs': [],
        'prod_py': [],
        'test_py': [],
        'other': [],
    }

    for f in files:
        parts = f.replace('\\', '/').split('/')
        in_tests_dir = any(p.lower() in ('tests', 'test') for p in parts[:-1])

        if f.endswith('.cs'):
            if in_tests_dir:
                classified['test_cs'].append(f)
            else:
                classified['prod_cs'].append(f)
        elif f.endswith('.py'):
            if in_tests_dir:
                classified['test_py'].append(f)
            else:
                classified['prod_py'].append(f)
        else:
            classified['other'].append(f)

    return classified


def check_mixed_concerns(classified: dict) -> list[str]:
    """
    Return a list of warning messages for mixed-concern commits.

    Warns when:
    - prod_cs and test_cs are both non-empty (mixed C# prod+test)
    - prod_py and test_py are both non-empty (mixed Python prod+test)
    - C# files (prod or test) and Python files (prod or test) coexist
    """
    warnings: list[str] = []

    has_prod_cs = bool(classified['prod_cs'])
    has_test_cs = bool(classified['test_cs'])
    has_prod_py = bool(classified['prod_py'])
    has_test_py = bool(classified['test_py'])

    has_any_cs = has_prod_cs or has_test_cs
    has_any_py = has_prod_py or has_test_py

    # Mixed prod+test within C#
    if has_prod_cs and has_test_cs:
        prod_names = ', '.join(classified['prod_cs'])
        test_names = ', '.join(classified['test_cs'])
        warnings.append(
            "WARNING: Mixed prod+test files in single commit\n"
            f"  Production: {prod_names}\n"
            f"  Test: {test_names}\n"
            "Consider separate commits for prod and test changes."
        )

    # Mixed prod+test within Python
    if has_prod_py and has_test_py:
        prod_names = ', '.join(classified['prod_py'])
        test_names = ', '.join(classified['test_py'])
        warnings.append(
            "WARNING: Mixed prod+test files in single commit\n"
            f"  Production: {prod_names}\n"
            f"  Test: {test_names}\n"
            "Consider separate commits for prod and test changes."
        )

    # Mixed C# + Python
    if has_any_cs and has_any_py:
        cs_files = classified['prod_cs'] + classified['test_cs']
        py_files = classified['prod_py'] + classified['test_py']
        cs_names = ', '.join(cs_files)
        py_names = ', '.join(py_files)
        warnings.append(
            "WARNING: Mixed C#+Python files in single commit\n"
            f"  C#: {cs_names}\n"
            f"  Python: {py_names}\n"
            "Consider separate commits for C# and Python changes."
        )

    return warnings


def main() -> int:
    staged = get_staged_files()
    file_count = len(staged)

    if file_count > MAX_FILES:
        print()
        print("=" * 62)
        print(f"BLOCKED: Too many files staged ({file_count} > {MAX_FILES})")
        print("=" * 62)
        print("Consider splitting this into smaller, focused commits.")
        print("=" * 62)
        print()
        return 1

    classified = classify_files(staged)
    warnings = check_mixed_concerns(classified)

    for warning in warnings:
        print()
        print(warning)

    return 0


if __name__ == '__main__':
    sys.exit(main())
