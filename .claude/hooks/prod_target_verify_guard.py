#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Production target verification guard.

Fires on Bash tool. When a command contains 'dotnet' AND sets
WSL_SQL_CONNECTION or RT_DESIGN_CONNECTION to a value containing
'.database.windows.net', outputs an advisory reminding Claude to verify
the target database via az CLI before proceeding.

Also reminds that PROD_SQL_CONNECTION belongs to stock-analyzer, not road-trip.

Advisory only — always exits 0. Injects additionalContext JSON to stdout.
"""

import json
import re
import sys


# Detects: WSL_SQL_CONNECTION=<val> or RT_DESIGN_CONNECTION=<val>
# where <val> contains .database.windows.net
AZURE_SQL_ENV_PATTERN = re.compile(
    r'(?:WSL_SQL_CONNECTION|RT_DESIGN_CONNECTION)\s*=\s*["\']?[^"\';\s]*'
    r'\.database\.windows\.net',
    re.IGNORECASE
)


def command_has_dotnet(command):
    return bool(re.search(r'\bdotnet\b', command, re.IGNORECASE))


def command_sets_azure_sql(command):
    return bool(AZURE_SQL_ENV_PATTERN.search(command))


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    if not command_has_dotnet(command):
        sys.exit(0)

    if not command_sets_azure_sql(command):
        sys.exit(0)

    # Extract which variable was matched for the advisory
    matched_var = "WSL_SQL_CONNECTION or RT_DESIGN_CONNECTION"
    if re.search(r'\bWSL_SQL_CONNECTION\b', command):
        matched_var = "WSL_SQL_CONNECTION"
    elif re.search(r'\bRT_DESIGN_CONNECTION\b', command):
        matched_var = "RT_DESIGN_CONNECTION"

    context = (
        f"ADVISORY: Detected dotnet command targeting an Azure SQL database "
        f"via {matched_var}.\n\n"
        f"Before running this command, verify you are targeting the correct "
        f"database:\n\n"
        f"  az sql db show \\\n"
        f"    --resource-group <rg> \\\n"
        f"    --server <server-name> \\\n"
        f"    --name <db-name>\n\n"
        f"REMINDER: Connection string ownership:\n"
        f"  PROD_SQL_CONNECTION   → stock-analyzer (NOT road-trip)\n"
        f"  WSL_SQL_CONNECTION    → road-trip production SQL\n"
        f"  RT_DESIGN_CONNECTION  → road-trip design/staging SQL\n\n"
        f"Confirm the server name in the connection string matches the "
        f"intended environment before proceeding. Targeting the wrong Azure "
        f"SQL instance can result in data loss or corruption in production."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
