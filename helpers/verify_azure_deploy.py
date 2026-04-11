#!/usr/bin/env python3
"""
Post-deploy verification script for Azure Key Vault and App Service configuration.

Verifies that Key Vault exists, endpoints.json vault names match deployed vault,
required secrets exist, and both App Service and Deploy SP have proper RBAC roles.

Exit codes:
  0 = all checks pass
  1 = one or more checks failed
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


# Azure built-in role ID for Key Vault Secrets User
KV_SECRETS_USER_ROLE_ID = "4633458b-17de-408a-b874-0445c86b69e6"


def run_az_command(args, timeout=30):
    """Run an az CLI command and return stdout as parsed JSON or None on error."""
    try:
        result = subprocess.run(
            ["az"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def find_keyvault_in_resource_group(resource_group):
    """Find the first Key Vault in the resource group."""
    vaults = run_az_command(
        ["keyvault", "list", "--resource-group", resource_group]
    )
    if not vaults or not isinstance(vaults, list) or len(vaults) == 0:
        return None
    return vaults[0]


def check_keyvault_exists(resource_group, vault_name):
    """Check if a specific Key Vault exists in the resource group."""
    vault = run_az_command(
        ["keyvault", "show", "--resource-group", resource_group, "--name", vault_name]
    )
    return vault is not None


def check_secret_exists(vault_name, secret_name):
    """Check if a secret exists in the Key Vault."""
    secret = run_az_command(
        ["keyvault", "secret", "show", "--vault-name", vault_name, "--name", secret_name]
    )
    return secret is not None


def check_role_assignment(scope, principal_id, role_id):
    """Check if a principal has a specific role assignment on a scope."""
    assignments = run_az_command(
        ["role", "assignment", "list", "--scope", scope]
    )
    if not assignments or not isinstance(assignments, list):
        return False

    for assignment in assignments:
        role_def = assignment.get("roleDefinitionId", "")
        principal = assignment.get("principalId", "")
        if role_id in role_def and principal_id in principal:
            return True
    return False


def get_app_service_principal_id(resource_group, app_service_name):
    """Get the managed identity principal ID of an App Service."""
    app = run_az_command(
        ["webapp", "identity", "show", "--resource-group", resource_group, "--name", app_service_name]
    )
    if app and "principalId" in app:
        return app["principalId"]
    return None


def get_keyvault_resource_id(resource_group, vault_name):
    """Get the full resource ID of a Key Vault."""
    vault = run_az_command(
        ["keyvault", "show", "--resource-group", resource_group, "--name", vault_name]
    )
    if vault and "id" in vault:
        return vault["id"]
    return None


def load_endpoints_json(repo_root):
    """Load endpoints.json from repo root."""
    endpoints_path = Path(repo_root) / "endpoints.json"
    if not endpoints_path.exists():
        return None

    try:
        with open(endpoints_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def extract_keyvault_entries(endpoints_data):
    """Extract all keyvault source entries from endpoints.json."""
    entries = []

    if not endpoints_data or "environments" not in endpoints_data:
        return entries

    for env_name, env_block in endpoints_data["environments"].items():
        if not isinstance(env_block, dict):
            continue

        for ep_name, ep_value in env_block.items():
            _extract_keyvault_entries_recursive(
                ep_value, env_name, ep_name, entries
            )

    return entries


def _extract_keyvault_entries_recursive(obj, env_name, path, entries, parent_path=""):
    """Recursively extract keyvault entries from nested structures."""
    if not isinstance(obj, dict):
        return

    current_path = f"{parent_path}{path}" if parent_path else f"{env_name}.{path}"

    if obj.get("source") == "keyvault":
        vault = obj.get("vault")
        secret = obj.get("secret")
        if vault and secret:
            entries.append({
                "path": current_path,
                "vault": vault,
                "secret": secret,
                "environment": env_name
            })
    else:
        # Check nested entries
        for sub_name, sub_value in obj.items():
            if sub_name == "description":
                continue
            if isinstance(sub_value, dict):
                _extract_keyvault_entries_recursive(
                    sub_value, env_name, sub_name, entries,
                    parent_path=f"{current_path}."
                )


def main():
    parser = argparse.ArgumentParser(
        description="Verify Azure Key Vault and App Service configuration after deployment."
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Azure resource group name"
    )
    parser.add_argument(
        "--endpoints",
        required=False,
        help="Path to endpoints.json for vault/secret verification (optional)"
    )
    parser.add_argument(
        "--deploy-sp-object-id",
        required=True,
        help="Object ID of the Deploy Service Principal"
    )
    parser.add_argument(
        "--app-service-name",
        required=False,
        help="App Service name for managed identity verification (optional)"
    )

    args = parser.parse_args()

    checks = []
    all_pass = True

    # Check 1: Key Vault exists
    print("\n[1/5] Checking Key Vault exists in resource group...", end=" ", flush=True)
    vault = find_keyvault_in_resource_group(args.resource_group)
    if vault:
        vault_name = vault.get("name", "")
        print(f"PASS\n      Found: {vault_name}")
        checks.append(("Key Vault exists", True))
    else:
        print("FAIL")
        print("      No Key Vault found in resource group.")
        print(f"      Fix: Create a Key Vault in {args.resource_group} or specify correct resource group.")
        checks.append(("Key Vault exists", False))
        all_pass = False
        return 1 if all_pass is False else 0

    # Check 2: endpoints.json vault names match deployed vault
    if args.endpoints:
        print("[2/5] Checking endpoints.json vault names match deployed vault...", end=" ", flush=True)
        endpoints_data = load_endpoints_json(args.endpoints)
        if endpoints_data:
            kv_entries = extract_keyvault_entries(endpoints_data)
            mismatches = []
            for entry in kv_entries:
                if entry["vault"] != vault_name:
                    mismatches.append(entry)

            if not mismatches:
                print("PASS")
                checks.append(("endpoints.json vault names match", True))
            else:
                print("FAIL")
                for entry in mismatches:
                    print(f"      {entry['path']}: vault name mismatch (expected '{vault_name}')")
                print(f"      Fix: Update endpoints.json vault names to '{vault_name}' for all keyvault entries.")
                checks.append(("endpoints.json vault names match", False))
                all_pass = False
        else:
            print("SKIP (could not load endpoints.json)")
    else:
        print("[2/5] Skipping endpoints.json check (not provided)")

    # Check 3: Required secrets exist
    print("[3/5] Checking required secrets exist in Key Vault...", end=" ", flush=True)
    if args.endpoints:
        endpoints_data = load_endpoints_json(args.endpoints)
        if endpoints_data:
            kv_entries = extract_keyvault_entries(endpoints_data)
            missing_secrets = []
            for entry in kv_entries:
                if not check_secret_exists(vault_name, entry["secret"]):
                    missing_secrets.append(entry)

            if not missing_secrets:
                print("PASS")
                print(f"      All {len(kv_entries)} required secrets found")
                checks.append(("Required secrets exist", True))
            else:
                print("FAIL")
                for entry in missing_secrets:
                    print(f"      Missing: [REDACTED] (referenced in {entry['path']})")
                print(f"      Fix: Create the missing secrets in Key Vault '{vault_name}'.")
                print(f"           Review endpoints.json for the {len(missing_secrets)} missing secret name(s).")
                checks.append(("Required secrets exist", False))
                all_pass = False
        else:
            print("SKIP (could not load endpoints.json)")
    else:
        print("SKIP (endpoints.json not provided)")

    # Check 4: App Service managed identity has Key Vault Secrets User role
    if args.app_service_name:
        print("[4/5] Checking App Service managed identity has Key Vault Secrets User role...", end=" ", flush=True)
        app_principal_id = get_app_service_principal_id(args.resource_group, args.app_service_name)
        if app_principal_id:
            kv_id = get_keyvault_resource_id(args.resource_group, vault_name)
            if kv_id and check_role_assignment(kv_id, app_principal_id, KV_SECRETS_USER_ROLE_ID):
                print("PASS")
                checks.append(("App Service has KV Secrets User role", True))
            else:
                print("FAIL")
                print(f"      App Service '{args.app_service_name}' managed identity missing role.")
                print(f"      Fix: az role assignment create --assignee-object-id {app_principal_id} \\")
                print(f"           --role '4633458b-17de-408a-b874-0445c86b69e6' \\")
                print(f"           --scope {kv_id}")
                checks.append(("App Service has KV Secrets User role", False))
                all_pass = False
        else:
            print("SKIP (could not get App Service principal ID)")
    else:
        print("[4/5] Skipping App Service check (not provided)")

    # Check 5: Deploy SP has Key Vault Secrets User role
    print("[5/5] Checking Deploy SP has Key Vault Secrets User role...", end=" ", flush=True)
    kv_id = get_keyvault_resource_id(args.resource_group, vault_name)
    if kv_id and check_role_assignment(kv_id, args.deploy_sp_object_id, KV_SECRETS_USER_ROLE_ID):
        print("PASS")
        checks.append(("Deploy SP has KV Secrets User role", True))
    else:
        print("FAIL")
        print(f"      Deploy SP (OID: {args.deploy_sp_object_id}) missing Key Vault Secrets User role.")
        print(f"      Fix: az role assignment create --assignee-object-id {args.deploy_sp_object_id} \\")
        print(f"           --role '4633458b-17de-408a-b874-0445c86b69e6' \\")
        print(f"           --scope {kv_id}")
        checks.append(("Deploy SP has KV Secrets User role", False))
        all_pass = False

    # Summary
    print("\n" + "=" * 70)
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    print(f"Summary: {passed}/{total} checks passed")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
