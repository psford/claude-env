#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Enforce EF Core migrations over raw SQL.

Enforces rule:
- Database schema changes must use EF Core migrations, not raw SQL scripts
- Blocks sqlcmd, Invoke-Sqlcmd, and similar direct SQL execution on migration scripts

This project uses Entity Framework Core for database migrations.
"""

import json
import sys
import re

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # Patterns that indicate direct SQL execution for migrations
    sql_migration_patterns = [
        # Direct SQL file execution
        r'sqlcmd.*\.sql',
        r'Invoke-Sqlcmd.*\.sql',
        r'osql.*\.sql',
        # SQL execution with migration-like file names
        r'sqlcmd.*[Mm]igration',
        r'sqlcmd.*[Aa]dd.*[Tt]able',
        r'sqlcmd.*[Cc]reate.*[Tt]able',
        r'sqlcmd.*[Aa]lter.*[Tt]able',
        r'sqlcmd.*[Ss]taging',
        # Azure SQL execution
        r'az sql.*query.*\.sql',
        # Generic patterns for schema changes via SQL files
        r'(sqlcmd|Invoke-Sqlcmd).*(-i|-InputFile).*\.sql',
    ]

    is_sql_migration = any(re.search(p, command, re.IGNORECASE) for p in sql_migration_patterns)

    if not is_sql_migration:
        return 0

    # Block the operation and provide guidance
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "message": """
EF CORE MIGRATION GUARD

BLOCKED: This command appears to execute raw SQL for database schema changes.

This project uses Entity Framework Core for database migrations.

Instead of running SQL directly, use EF Core migrations:

1. Add a migration:
   dotnet ef migrations add <MigrationName> --project ../StockAnalyzer.Core/StockAnalyzer.Core.csproj --startup-project . --output-dir ../StockAnalyzer.Core/Data/Migrations

2. Apply migrations:
   dotnet ef database update --project ../StockAnalyzer.Core/StockAnalyzer.Core.csproj --startup-project .

3. Or let the app apply on startup (if configured)

Benefits of EF Core migrations:
- Version controlled, reversible
- Works across environments (dev, prod)
- Tracks applied migrations in __EFMigrationsHistory table
- Generates proper rollback scripts

If you need to run a one-off query (not schema change), use sqlcmd without a .sql file.
"""
        }
    }

    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
