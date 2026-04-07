#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Endpoint registry guard.

Fires on git commit. Scans staged files for hardcoded connection strings
and direct env var reads for known endpoint keys. Blocks commits that
contain these patterns (except in endpoints.json itself).

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

    # Load known env var keys from endpoints.json
    known_keys = load_env_keys(endpoints_path)

    # Get staged diff
    diff = get_staged_diff()
    if not diff:
        return 0

    violations = scan_diff(diff, known_keys)

    if violations:
        print("\n❌ ENDPOINT REGISTRY GUARD: Hardcoded connection/credential patterns found", file=sys.stderr)
        print("   Use EndpointRegistry.Resolve() instead of direct env var reads or hardcoded strings.\n", file=sys.stderr)
        for v in violations:
            print(f"   {v['file']}:{v['line']}: {v['reason']}", file=sys.stderr)
            print(f"      {v['content'].strip()}", file=sys.stderr)
        print(f"\n   {len(violations)} violation(s) found. Commit blocked.", file=sys.stderr)
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


def load_env_keys(endpoints_path):
    """Extract env var key names from endpoints.json entries with source=env."""
    try:
        with open(endpoints_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = set()
        for env_name, env_block in data.get("environments", {}).items():
            for ep_name, ep_value in env_block.items():
                _extract_keys(ep_value, keys)
        return keys
    except Exception:
        return set()


def _extract_keys(obj, keys):
    if isinstance(obj, dict):
        if obj.get("source") == "env" and "key" in obj:
            keys.add(obj["key"])
        else:
            for v in obj.values():
                _extract_keys(v, keys)


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


# Connection string patterns (case-insensitive)
CONN_PATTERNS = [
    re.compile(r'Server\s*=\s*tcp:', re.IGNORECASE),
    re.compile(r'\.database\.windows\.net', re.IGNORECASE),
    re.compile(r'Initial\s+Catalog\s*=', re.IGNORECASE),
    re.compile(r'DefaultEndpointsProtocol\s*=', re.IGNORECASE),
    re.compile(r'AccountKey\s*=', re.IGNORECASE),
    re.compile(r'Configuration\.GetConnectionString\(', re.IGNORECASE),
    re.compile(r'config\["ConnectionStrings', re.IGNORECASE),
]

SKIP_EXTENSIONS = {".md", ".txt", ".json"}
SKIP_FILENAMES = {"endpoints.json", "test-endpoints.json", "endpoints.schema.json"}


def scan_diff(diff_text, known_keys):
    violations = []
    current_file = None
    line_num = 0

    # Build env var pattern from known keys
    if known_keys:
        env_pattern = re.compile(
            r'GetEnvironmentVariable\(\s*"(' + "|".join(re.escape(k) for k in known_keys) + r')"\s*\)'
        )
    else:
        env_pattern = None

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            current_file = None
        elif line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            # Parse line number from hunk header
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            line_num += 1
            if current_file and should_check(current_file):
                content = line[1:]  # Remove leading +

                # Skip comment lines
                stripped = content.strip()
                if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("<!--"):
                    continue

                # Check connection string patterns
                for pattern in CONN_PATTERNS:
                    if pattern.search(content):
                        violations.append({
                            "file": current_file,
                            "line": line_num,
                            "content": content,
                            "reason": "Hardcoded connection string pattern"
                        })
                        break

                # Check direct env var reads for known endpoint keys
                if env_pattern and env_pattern.search(content):
                    violations.append({
                        "file": current_file,
                        "line": line_num,
                        "content": content,
                        "reason": "Direct env var read for endpoint key — use EndpointRegistry.Resolve()"
                    })

    return violations


def should_check(filepath):
    filename = os.path.basename(filepath)
    if filename in SKIP_FILENAMES:
        return False
    _, ext = os.path.splitext(filename)
    if ext in SKIP_EXTENSIONS:
        return False
    if "/Fixtures/" in filepath or "/fixtures/" in filepath:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
