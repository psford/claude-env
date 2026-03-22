#!/usr/bin/env python3
"""
Full working-tree stale path scanner.

Reads patterns from .claude/stale_path_patterns.json and scans all
git-tracked files for references to claudeProjects monorepo paths.

Usage:
    python helpers/scan_stale_paths.py
    python helpers/scan_stale_paths.py --path helpers/
    python helpers/scan_stale_paths.py --fix-hint

Exit codes:
    0 — no violations found
    1 — one or more violations found
"""

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERNS_FILE = os.path.join(REPO_ROOT, ".claude", "stale_path_patterns.json")

SCANNED_EXTENSIONS = re.compile(
    r'\.(md|yml|yaml|json|cs|py|sh|ps1|csproj|sln|xml|html|js|ts|bicep)$',
    re.IGNORECASE,
)

ESCAPE_HATCH = re.compile(r'#\s*STALE-PATH-OK\s*:', re.IGNORECASE)


def load_patterns():
    """Load and compile patterns from JSON config."""
    if not os.path.exists(PATTERNS_FILE):
        print(f"ERROR: Patterns file not found: {PATTERNS_FILE}", file=sys.stderr)
        sys.exit(2)
    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    patterns = data.get("patterns", [])
    compiled = []
    for p in patterns:
        try:
            compiled.append((re.compile(p["pattern"]), p))
        except re.error as e:
            print(f"WARNING: Skipping malformed pattern '{p['pattern']}': {e}", file=sys.stderr)
    return compiled


def get_tracked_files(path_filter=None):
    """Return list of git-tracked files, optionally filtered to a sub-path."""
    cmd = ["git", "ls-files"]
    if path_filter:
        cmd.append(path_filter)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT
    )
    if result.returncode != 0:
        print("ERROR: git ls-files failed", file=sys.stderr)
        sys.exit(2)
    return [f for f in result.stdout.strip().split("\n") if f]


def scan_file(filepath, compiled_patterns):
    """
    Scan a single file for stale path violations.
    Returns list of (line_number, line_content, pattern_entry).
    """
    full_path = os.path.join(REPO_ROOT, filepath)
    violations = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                stripped = line.rstrip("\n")
                if ESCAPE_HATCH.search(stripped):
                    continue
                for compiled_re, pattern_entry in compiled_patterns:
                    if compiled_re.search(stripped):
                        violations.append((lineno, stripped, pattern_entry))
                        break  # One match per line
    except OSError:
        pass
    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Scan git-tracked files for stale claudeProjects monorepo paths."
    )
    parser.add_argument(
        "--path",
        metavar="PATH",
        help="Limit scan to files under this path (relative to repo root)",
        default=None,
    )
    parser.add_argument(
        "--fix-hint",
        action="store_true",
        help="Print remedy hints alongside each violation",
    )
    args = parser.parse_args()

    compiled_patterns = load_patterns()
    if not compiled_patterns:
        print("No patterns loaded — nothing to scan.", file=sys.stderr)
        sys.exit(0)

    tracked_files = get_tracked_files(args.path)
    scanned_files = [f for f in tracked_files if SCANNED_EXTENSIONS.search(f)]

    all_violations = {}  # filepath -> list of (lineno, content, pattern_entry)

    for filepath in scanned_files:
        file_violations = scan_file(filepath, compiled_patterns)
        if file_violations:
            all_violations[filepath] = file_violations

    if not all_violations:
        print(f"Clean — no stale paths found. ({len(scanned_files)} files scanned)")
        sys.exit(0)

    # Report grouped by file
    total = sum(len(v) for v in all_violations.values())
    print(f"STALE PATHS FOUND: {total} violation(s) in {len(all_violations)} file(s)\n")

    for filepath in sorted(all_violations):
        print(f"  {filepath}")
        for lineno, content, pattern_entry in all_violations[filepath]:
            print(f"    Line {lineno:4d}: {content.strip()}")
            print(f"    Pattern  : {pattern_entry['pattern']}")
            if args.fix_hint:
                print(f"    Remedy   : {pattern_entry['remedy']}")
            print()

    print("To suppress an intentional reference, add to that line:")
    print("    # STALE-PATH-OK: <reason>")
    print()
    print("To add a new pattern:")
    print("    python helpers/add_stale_pattern.py --pattern '...' --description '...' --remedy '...'")

    sys.exit(1)


if __name__ == "__main__":
    main()
