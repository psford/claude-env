#!/usr/bin/env python3
"""
CLI tool to add a new stale path pattern to .claude/stale_path_patterns.json.

Usage:
    python helpers/add_stale_pattern.py \
        --pattern "projects/my-project/" \
        --description "My project path from the monorepo" \
        --remedy "Remove this path; use a relative path instead."

Validates:
  - Regex compiles without error
  - Pattern is not already present (duplicate check)

Appends the new entry to the patterns array and reminds you to commit.
"""

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERNS_FILE = os.path.join(REPO_ROOT, ".claude", "stale_path_patterns.json")


def load_config():
    if not os.path.exists(PATTERNS_FILE):
        print(f"ERROR: Patterns file not found: {PATTERNS_FILE}", file=sys.stderr)
        sys.exit(2)
    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_regex(pattern):
    try:
        re.compile(pattern)
    except re.error as e:
        print(f"ERROR: Pattern is not a valid regex: {e}", file=sys.stderr)
        sys.exit(1)


def check_duplicate(patterns, new_pattern):
    for existing in patterns:
        if existing.get("pattern") == new_pattern:
            print(f"ERROR: Pattern already exists: {new_pattern}", file=sys.stderr)
            print("Existing entry:")
            print(f"  description: {existing.get('description', '')}")
            print(f"  remedy     : {existing.get('remedy', '')}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Add a new stale path pattern to the detection config."
    )
    parser.add_argument(
        "--pattern",
        required=True,
        metavar="REGEX",
        help="Regex pattern to detect (e.g. 'projects/my-project/')",
    )
    parser.add_argument(
        "--description",
        required=True,
        metavar="TEXT",
        help="Human-readable description of what this pattern detects",
    )
    parser.add_argument(
        "--remedy",
        required=True,
        metavar="TEXT",
        help="Instructions for how to fix a violation",
    )
    args = parser.parse_args()

    validate_regex(args.pattern)

    data = load_config()
    patterns = data.get("patterns", [])

    check_duplicate(patterns, args.pattern)

    new_entry = {
        "pattern": args.pattern,
        "description": args.description,
        "remedy": args.remedy,
    }
    patterns.append(new_entry)
    data["patterns"] = patterns

    save_config(data)

    print(f"Pattern added ({len(patterns)} total patterns):")
    print(f"  pattern    : {args.pattern}")
    print(f"  description: {args.description}")
    print(f"  remedy     : {args.remedy}")
    print()
    print("REMINDER: Commit the updated patterns file:")
    print(f"  git add {os.path.relpath(PATTERNS_FILE, REPO_ROOT)}")
    print('  git commit -m "chore: add stale path pattern for ..."')


if __name__ == "__main__":
    main()
