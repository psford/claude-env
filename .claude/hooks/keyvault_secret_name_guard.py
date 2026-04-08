#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Key Vault secret name guard.

Fires on git commit. Validates KV secret names conform to Azure naming rules
(^[a-zA-Z0-9-]{1,127}$). Checks all "secret" fields in keyvault entries across
all environments.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
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

    # Get staged content of endpoints.json
    staged_content = get_staged_content("endpoints.json")
    if not staged_content:
        return 0

    try:
        endpoints_data = json.loads(staged_content)
    except json.JSONDecodeError:
        return 0

    # Validate secret names
    invalid_secrets = validate_secret_names(endpoints_data)

    if invalid_secrets:
        print("\n❌ KEYVAULT SECRET NAME GUARD: Invalid Azure Key Vault secret names", file=sys.stderr)
        print("   Secret names must match: ^[a-zA-Z0-9-]{1,127}$ (letters, digits, hyphens only, 1-127 chars)\n", file=sys.stderr)
        for entry in sorted(invalid_secrets):
            print(f"   - {entry['path']}: '{entry['name']}' (reason: {entry['reason']})", file=sys.stderr)
        print(f"\n   {len(invalid_secrets)} invalid secret(s). Commit blocked.", file=sys.stderr)
        return 2

    return 0


def get_staged_content(filename):
    """Get the staged content of a file."""
    try:
        result = subprocess.run(
            ["git", "show", f":{filename}"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


def validate_secret_names(endpoints_data):
    """Validate all keyvault secret names."""
    invalid_secrets = []
    secret_pattern = re.compile(r"^[a-zA-Z0-9-]{1,127}$")

    def check_entry(obj, env_name, parent_path=""):
        if isinstance(obj, dict):
            if obj.get("source") == "keyvault" and "secret" in obj:
                secret = obj["secret"]
                path = f"{env_name}.{parent_path}" if parent_path else env_name
                
                if not secret_pattern.match(secret):
                    reason = ""
                    if len(secret) > 127:
                        reason = "too long (>127 chars)"
                    elif len(secret) == 0:
                        reason = "empty"
                    elif "_" in secret:
                        reason = "contains underscore"
                    elif "." in secret:
                        reason = "contains period"
                    elif not re.match(r"^[a-zA-Z0-9-]*$", secret):
                        reason = "invalid character"
                    else:
                        reason = "invalid format"
                    
                    invalid_secrets.append({
                        "path": path,
                        "name": secret,
                        "reason": reason
                    })
            else:
                for sub_name, sub_value in obj.items():
                    if sub_name != "description":
                        new_path = f"{parent_path}.{sub_name}" if parent_path else sub_name
                        check_entry(sub_value, env_name, new_path)

    for env_name, env_block in endpoints_data.get("environments", {}).items():
        for ep_name, ep_value in env_block.items():
            check_entry(ep_value, env_name, ep_name)

    return invalid_secrets


if __name__ == "__main__":
    sys.exit(main())
