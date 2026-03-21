#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Assert-without-verify guard.

Fires on Write/Edit to artifact files and Bash commands with hardcoded Azure
resource names. Injects mandatory context requiring Claude to verify current
state before claiming a write is meaningful.

Advisory only — does not block.
"""

import json
import sys
import re
import os


ARTIFACT_WRITE_PATTERNS = [
    r'sessionState\.md$',
    r'claudeLog\.md$',
    r'whileYouWereAway\.md$',
    r'installed_plugins\.json$',
    r'marketplace\.json$',
    r'TECHNICAL_SPEC\.md$',
    r'FUNCTIONAL_SPEC\.md$',
    r'retrospective-log\.md$',
]

AZURE_HARDCODED_NAME_PATTERN = re.compile(
    r'\baz\b.+?--(name|vault-name|server|resource-group|registry)\s+["\']?[a-zA-Z0-9_-]+["\']?',
    re.IGNORECASE
)

AZURE_QUERY_PATTERN = re.compile(
    r'\baz\b.+?\b(list|show)\b.+?--query',
    re.IGNORECASE
)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Check artifact writes (Write/Edit tools)
    if tool_name in ("Write", "Edit", "MultiEdit"):
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if not file_path:
            return 0

        normalized = file_path.replace("\\", "/")
        matched = False
        for pattern in ARTIFACT_WRITE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                matched = True
                break

        if not matched:
            return 0

        filename = os.path.basename(file_path)
        context = (
            f"ASSERT-WITHOUT-VERIFY GUARD\n\n"
            f"Writing to artifact: {file_path}\n\n"
            f"Before this write is meaningful:\n"
            f"1. Read the CURRENT contents of {filename} with the Read tool\n"
            f"2. Confirm this path is what the downstream consumer actually reads\n"
            f"3. Preserve existing content that should not be replaced\n\n"
            f"Do NOT write from memory of what you think the file contains."
        )

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": context
            }
        }
        print(json.dumps(output))
        return 0

    # Check Azure hardcoded names (Bash tool)
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not command:
            return 0

        if AZURE_QUERY_PATTERN.search(command):
            return 0

        if not AZURE_HARDCODED_NAME_PATTERN.search(command):
            return 0

        context = (
            f"ASSERT-WITHOUT-VERIFY GUARD — HARDCODED AZURE RESOURCE NAME\n\n"
            f"Command: {command[:200]}\n\n"
            f"You appear to be using an Azure resource name from memory.\n"
            f"Azure resource names can include random suffixes.\n\n"
            f"REQUIRED: Query the actual name first:\n"
            f"  az sql server list --query \"[].name\" -o tsv\n"
            f"  az sql db list --server <server> --query \"[].name\" -o tsv\n"
            f"  az group list --query \"[].name\" -o tsv\n\n"
            f"Use the CLI-returned name, not one recalled from memory."
        )

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": context
            }
        }
        print(json.dumps(output))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
