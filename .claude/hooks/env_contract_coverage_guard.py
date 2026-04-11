#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Environment contract coverage guard.

Fires on git commit. Extracts every "key" from "source": "env" entries in the
dev environment block of endpoints.json, then checks all *.cs test files under
tests/ for matching SetEnvironmentVariable calls. Blocks if any key is missing
from tests.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import os
import re
import subprocess
import sys


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git commit" not in command:
        return 0

    repo_root = get_repo_root()
    if not repo_root:
        return 0

    endpoints_path = os.path.join(repo_root, "endpoints.json")
    if not os.path.exists(endpoints_path):
        return 0  # No endpoints.json — hook doesn't apply

    # Get staged files
    staged = get_staged_files()
    if "endpoints.json" not in staged:
        return 0  # endpoints.json not being modified

    # Extract env keys from dev environment
    env_keys = load_dev_env_keys(endpoints_path)
    if not env_keys:
        return 0  # No env keys to check

    # Get all .cs test files
    test_dir = os.path.join(repo_root, "tests")
    if not os.path.exists(test_dir):
        return 0  # No tests directory

    # Check coverage of each key
    coverage = check_test_coverage(test_dir, env_keys)
    missing_keys = {k for k in env_keys if not coverage[k]}

    if missing_keys:
        print("\n❌ ENV CONTRACT COVERAGE GUARD: Missing SetEnvironmentVariable calls in tests", file=sys.stderr)
        print("   Every 'env' source key in endpoints.json dev block must have a SetEnvironmentVariable()", file=sys.stderr)
        print("   call in at least one test file to document the contract.\n", file=sys.stderr)
        for key in sorted(missing_keys):
            print(f"   - {key}: No SetEnvironmentVariable(\"{key}\") found in test files", file=sys.stderr)
        print(f"\n   {len(missing_keys)} key(s) missing. Commit blocked.", file=sys.stderr)
        return 2

    return 0


def get_repo_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5
        )
        return set(result.stdout.strip().split("\n")) if result.returncode == 0 else set()
    except Exception:
        return set()


def load_dev_env_keys(endpoints_path):
    """Extract env var key names from endpoints.json dev environment."""
    try:
        with open(endpoints_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = set()
        dev_block = data.get("environments", {}).get("dev", {})
        for ep_name, ep_value in dev_block.items():
            _extract_keys(ep_value, keys)
        return keys
    except Exception:
        return set()


def _extract_keys(obj, keys):
    """Recursively extract 'key' fields from 'source': 'env' entries."""
    if isinstance(obj, dict):
        if obj.get("source") == "env" and "key" in obj:
            keys.add(obj["key"])
        else:
            for v in obj.values():
                _extract_keys(v, keys)


def check_test_coverage(test_dir, env_keys):
    """Check which env keys have SetEnvironmentVariable calls in tests."""
    coverage = {k: False for k in env_keys}

    # Walk tests directory for .cs files, skip bin/ and obj/
    for root, dirs, files in os.walk(test_dir):
        # Skip build artifacts
        dirs[:] = [d for d in dirs if d not in {"bin", "obj"}]

        for filename in files:
            if filename.endswith(".cs"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Check for SetEnvironmentVariable("KEY") pattern for each key
                    for key in env_keys:
                        if not coverage[key]:
                            pattern = rf'SetEnvironmentVariable\s*\(\s*"?{re.escape(key)}"?\s*,'
                            if re.search(pattern, content, re.IGNORECASE):
                                coverage[key] = True
                except Exception:
                    pass

    return coverage


if __name__ == "__main__":
    sys.exit(main())
