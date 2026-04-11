#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Azure Service Principal identity guard.

Blocks Azure CLI operations when the logged-in service principal doesn't
match the repo's expected service principal.

This prevents accidents like running deployment against the wrong Azure
tenant or service principal, which could cause cross-project infrastructure
issues.

Hook event: PreToolUse (fires BEFORE tool executes)
Matcher: Bash (only Azure CLI commands)
Exit code: 0 (allow), 2 (block with error)
Timeout: 20s (az account show can be slow)
"""

import json
import os
import re
import subprocess
import sys


# Azure operations that require SP identity validation
AZURE_COMMANDS = [
    r"\baz\s+login\b",
    r"\baz\s+account\s+show\b",
    r"\baz\s+account\s+set\b",
    r"\baz\s+webapp\b",
    r"\baz\s+keyvault\b",
    r"\baz\s+deployment\b",
    r"\baz\s+acr\b",
]


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    
    # Check if command is an Azure operation
    if not any(re.search(pattern, command) for pattern in AZURE_COMMANDS):
        return 0

    # Load expected SP identity for this repo
    repo_root = get_repo_root()
    if not repo_root:
        return 0

    config_path = os.path.join(repo_root, ".claude", "azure-identity.json")
    if not os.path.exists(config_path):
        return 0  # No config — hook doesn't apply to this repo

    expected_config = load_config(config_path)
    if not expected_config:
        return 0

    # Get current logged-in identity
    current_identity = get_current_identity()
    if not current_identity:
        # Can't determine — be lenient
        return 0

    # If user (not SP), allow it
    if current_identity.get("type") != "servicePrincipal":
        return 0

    # Check if current SP matches expected
    current_sp_name = current_identity.get("name", "").lower()
    current_sp_oid = current_identity.get("objectId", "")
    
    allowed_names = [n.lower() for n in expected_config.get("allowed_sp_names", [])]
    allowed_oids = expected_config.get("allowed_sp_object_ids", [])

    name_match = any(name in current_sp_name for name in allowed_names)
    oid_match = current_sp_oid in allowed_oids if allowed_oids else True

    if name_match and oid_match:
        return 0

    # Mismatch — block with clear warning
    print(
        f"\n❌ AZURE SP IDENTITY GUARD: Service principal mismatch",
        file=sys.stderr
    )
    print(
        f"   Current SP: {current_sp_name} (OID: {current_sp_oid})",
        file=sys.stderr
    )
    print(
        f"   Expected SP (repo: {expected_config.get('repo')}): {allowed_names}",
        file=sys.stderr
    )
    print(
        f"   Resource group: {expected_config.get('resource_group')}",
        file=sys.stderr
    )
    print(
        "\n   CRITICAL: Deploying with the wrong SP could cause cross-project infrastructure issues.",
        file=sys.stderr
    )
    print(
        "   Verify your Azure login before proceeding.",
        file=sys.stderr
    )
    return 2


def get_repo_root():
    """Get the repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def load_config(config_path):
    """Load azure-identity.json config."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_current_identity():
    """Get current logged-in Azure identity via az account show."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "-o", "json"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "name": data.get("user", {}).get("name", ""),
                "type": data.get("user", {}).get("type", ""),
                "objectId": data.get("user", {}).get("objectId", ""),
            }
    except Exception:
        pass
    return None


if __name__ == "__main__":
    sys.exit(main())
