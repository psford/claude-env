#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Infrastructure commit checklist.

Fires before git commit when staged files include infrastructure patterns.
Injects a mandatory advisory checklist (not blocking, exit 0).

Checks staged files against infrastructure patterns (bicep, workflows,
Docker, authentication/identity, appsettings.Production) and groups
violations into categories, each with specific checklist items.

Hook event: PreToolUse (fires BEFORE tool executes)
Matcher: Bash (only git commit commands)
Exit code: Always 0 (advisory)
"""

import json
import os
import re
import subprocess
import sys


# Infrastructure file patterns grouped by category
PATTERNS_BY_CATEGORY = {
    "bicep_arm": [
        r"\.bicep$",
        r"\.json$.*arm.*template",
    ],
    "github_actions": [
        r"\.github/workflows/",
    ],
    "auth_identity": [
        r"roleAssignment",
        r"principalId",
        r"Microsoft\.Authorization",
        r"Microsoft\.KeyVault",
        r"KeyVault",
    ],
    "docker": [
        r"Dockerfile",
        r"docker-compose",
    ],
    "appsettings": [
        r"appsettings\.Production\.json",
    ],
}

# Checklist items per category
CHECKLISTS = {
    "bicep_arm": [
        "Are all ARM/Bicep resources properly scoped (resource group, subscription)?",
        "Have companion repos been checked for similar resource definitions?",
        "Is a deployment plan documented (az deployment group create, etc.)?",
        "Are secrets/keys referenced via KeyVault, not hardcoded?",
    ],
    "github_actions": [
        "Is deployment triggered appropriately (main branch only)?",
        "Do all Azure operations use the correct service principal?",
        "Have secret references been validated (GITHUB_TOKEN, etc.)?",
        "Is the workflow tested against develop/main correctly?",
    ],
    "auth_identity": [
        "Is the role/permission principle correctly scoped?",
        "Have cross-repo identity matches been validated (.claude/azure-identity.json)?",
        "Are principal IDs and names both documented and validated?",
        "Does the change match planned resource group and subscription?",
    ],
    "docker": [
        "Is the image tagged for both development and production?",
        "Do build arguments avoid secrets (use build secrets instead)?",
        "Have multi-stage builds been optimized for size?",
        "Is the image scanned for vulnerabilities before deployment?",
    ],
    "appsettings": [
        "Are production secrets stored in Azure KeyVault, not in the file?",
        "Have all environment-specific settings been externalized?",
        "Is the deployment target (App Service, Container Instance) documented?",
        "Are connection strings and keys validated before committing?",
    ],
}


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

    # Get staged files
    staged_files = get_staged_files()
    if not staged_files:
        return 0

    # Match staged files to categories
    categories_found = categorize_files(staged_files)
    if not categories_found:
        return 0

    # Generate checklist
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": generate_checklist(categories_found)
        }
    }
    print(json.dumps(output))
    return 0


def get_staged_files():
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return []
    except Exception:
        return []


def categorize_files(files):
    """Categorize staged files by infrastructure pattern."""
    categories = {}
    for filepath in files:
        for category, patterns in PATTERNS_BY_CATEGORY.items():
            for pattern in patterns:
                if re.search(pattern, filepath):
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(filepath)
                    break
    return categories


def generate_checklist(categories_found):
    """Generate checklist advisory."""
    checklist_lines = []
    for category in sorted(categories_found.keys()):
        checklist_lines.append(f"\n## {format_category_name(category)}\n")
        for i, item in enumerate(CHECKLISTS.get(category, []), 1):
            checklist_lines.append(f"  [ ] {item}")

    return f"""
INFRASTRUCTURE COMMIT CHECKLIST
================================

Your staged changes touch infrastructure files. Before committing, verify:
{''.join(checklist_lines)}

This is an advisory checklist to prevent infrastructure misconfigurations.
All items should be addressed before deployment.
"""


def format_category_name(category):
    """Convert category name to display format."""
    replacements = {
        "bicep_arm": "ARM/Bicep Resources",
        "github_actions": "GitHub Actions Workflows",
        "auth_identity": "Authentication & Identity",
        "docker": "Docker & Containers",
        "appsettings": "Application Settings",
    }
    return replacements.get(category, category.title())


if __name__ == "__main__":
    sys.exit(main())
