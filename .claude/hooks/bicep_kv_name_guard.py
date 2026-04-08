#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Bicep Key Vault name guard.

Fires on git commit. Scans staged endpoints.json for keyvault source entries
(prod only), reads all *.bicep files in repo, checks that each vault name
appears literally in bicep content. Blocks if a name is absent.

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

    # Get staged content of endpoints.json
    staged_content = get_staged_content("endpoints.json")
    if not staged_content:
        return 0

    try:
        endpoints_data = json.loads(staged_content)
    except json.JSONDecodeError:
        return 0

    # Extract vault names from prod keyvault entries
    vault_names = extract_prod_vault_names(endpoints_data)
    if not vault_names:
        return 0  # No keyvault entries in prod

    # Get all *.bicep files in repo
    bicep_files = get_bicep_files(repo_root)
    if not bicep_files:
        return 2  # No bicep files found but we have vault references
        # Actually, if there are vault references but no bicep, that's suspicious
        # But let's allow it in case bicep files are elsewhere
        return 0

    # Read all bicep content
    bicep_content = read_bicep_content(bicep_files)

    # Check vault names
    missing_vaults = check_vault_references(vault_names, bicep_content)

    if missing_vaults:
        print("\n❌ BICEP KV NAME GUARD: Vault names in endpoints.json don't appear in Bicep files", file=sys.stderr)
        print("   Every keyvault vault name in prod environment must be defined in a *.bicep file.\n", file=sys.stderr)
        for vault in sorted(missing_vaults):
            print(f"   - {vault}: Not found in any *.bicep file", file=sys.stderr)
        print(f"\n   {len(missing_vaults)} vault(s) missing. Commit blocked.", file=sys.stderr)
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


def extract_prod_vault_names(endpoints_data):
    """Extract vault names from prod keyvault entries."""
    vault_names = set()
    prod_block = endpoints_data.get("environments", {}).get("prod", {})
    
    def extract_vaults(obj):
        if isinstance(obj, dict):
            if obj.get("source") == "keyvault" and "vault" in obj:
                vault_names.add(obj["vault"])
            else:
                for v in obj.values():
                    extract_vaults(v)
    
    for ep_value in prod_block.values():
        extract_vaults(ep_value)
    
    return vault_names


def get_bicep_files(repo_root):
    """Get all *.bicep files using git ls-files."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.bicep"],
            cwd=repo_root,
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [os.path.join(repo_root, f) for f in result.stdout.strip().split("\n") if f]
        return []
    except Exception:
        return []


def read_bicep_content(bicep_files):
    """Read content of all bicep files."""
    content = ""
    for filepath in bicep_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content += f.read() + "\n"
        except Exception:
            pass
    return content


def check_vault_references(vault_names, bicep_content):
    """Check which vault names are missing from bicep content."""
    missing = set()
    for vault_name in vault_names:
        # Check for literal appearance of the vault name in bicep
        if vault_name not in bicep_content:
            missing.add(vault_name)
    return missing


if __name__ == "__main__":
    sys.exit(main())
