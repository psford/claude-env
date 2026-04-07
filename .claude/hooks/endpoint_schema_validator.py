#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Endpoint schema validator.

Fires on git commit. Validates endpoints.json against its schema when the
file is being committed. Standard library only — no external dependencies.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import os
import re
import subprocess
import sys

VALID_SOURCES = {"literal", "env", "keyvault"}

SECRET_PATTERNS = [
    re.compile(r'Server\s*=.*Password\s*=', re.IGNORECASE),
    re.compile(r'AccountKey\s*=', re.IGNORECASE),
    re.compile(r'DefaultEndpointsProtocol\s*=', re.IGNORECASE),
    re.compile(r'^(sk|pk|rk|Bearer\s+)[A-Za-z0-9_\-]{20,}', re.IGNORECASE),
]

# Suspicious: long random strings that could be API keys (not URLs)
SUSPICIOUS_VALUE = re.compile(r'^[A-Za-z0-9_\-]{30,}$')


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
        return 0

    # Only validate if endpoints.json is staged
    staged = get_staged_files()
    if "endpoints.json" not in staged:
        return 0

    errors = validate_endpoints(endpoints_path)

    if errors:
        print("\n❌ ENDPOINT SCHEMA VALIDATOR: endpoints.json validation failed", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        print(f"\n   {len(errors)} error(s) found. Commit blocked.", file=sys.stderr)
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


def validate_endpoints(path):
    errors = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except Exception as e:
        return [f"Cannot read file: {e}"]

    # Required top-level keys
    for key in ("$schema", "project", "environments"):
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")

    if "environments" not in data:
        return errors

    envs = data["environments"]
    if not isinstance(envs, dict) or len(envs) == 0:
        errors.append("'environments' must be a non-empty object")
        return errors

    for env_name, env_block in envs.items():
        if not isinstance(env_block, dict):
            errors.append(f"Environment '{env_name}' must be an object")
            continue

        for ep_name, ep_value in env_block.items():
            ep_errors = validate_entry(ep_value, env_name, ep_name)
            errors.extend(ep_errors)

    return errors


def validate_entry(entry, env_name, ep_name, parent_path=""):
    """Validate a single endpoint entry (simple or compound)."""
    errors = []
    path = f"{parent_path}{ep_name}" if parent_path else f"{env_name}.{ep_name}"

    if not isinstance(entry, dict):
        errors.append(f"{path}: entry must be an object")
        return errors

    if "source" in entry:
        # Simple entry
        source = entry["source"]
        if source not in VALID_SOURCES:
            errors.append(f"{path}: invalid source '{source}' (must be one of: {', '.join(VALID_SOURCES)})")
            return errors

        if source == "literal":
            if "value" not in entry:
                errors.append(f"{path}: literal source missing 'value'")
            else:
                # Check for secrets in literal values (especially prod)
                value = entry["value"]
                if env_name == "prod":
                    for pattern in SECRET_PATTERNS:
                        if pattern.search(value):
                            errors.append(f"{path}: literal value in prod looks like a secret — use 'keyvault' source instead")
                            break
                    else:
                        if SUSPICIOUS_VALUE.match(value) and not value.startswith("http"):
                            errors.append(f"{path}: literal value in prod looks like an API key ({len(value)} chars) — use 'keyvault' source instead")

        elif source == "env":
            if "key" not in entry:
                errors.append(f"{path}: env source missing 'key'")

        elif source == "keyvault":
            if "vault" not in entry:
                errors.append(f"{path}: keyvault source missing 'vault'")
            if "secret" not in entry:
                errors.append(f"{path}: keyvault source missing 'secret'")

    else:
        # Compound entry — validate sub-entries
        has_sub = False
        for sub_name, sub_value in entry.items():
            if sub_name == "description":
                continue
            if isinstance(sub_value, dict) and "source" in sub_value:
                has_sub = True
                sub_errors = validate_entry(sub_value, env_name, sub_name, parent_path=f"{path}.")
                errors.extend(sub_errors)

        if not has_sub:
            errors.append(f"{path}: entry has no 'source' and no valid sub-entries")

    return errors


if __name__ == "__main__":
    sys.exit(main())
