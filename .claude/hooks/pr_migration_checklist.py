#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: PR migration checklist.

Fires on `gh pr create`. When the diff between current branch and main
includes new EF Core migration files (Migrations/*_*.cs), injects
additionalContext reminding that a seeder run may be needed after deploy.

Advisory (exit 0 with context), not a hard block.
"""

import json
import sys
import re
import subprocess


MIGRATION_PATTERN = re.compile(
    r'Migrations/\d+_\w+\.cs$',
    re.IGNORECASE
)

# Ignore Designer.cs and Snapshot files — only care about the main migration file
MIGRATION_EXCLUDE = re.compile(
    r'(\.Designer\.cs|ModelSnapshot\.cs)$',
    re.IGNORECASE
)


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_new_migrations():
    """Find migration files in the diff between HEAD and origin/main."""
    diff_output = run_git("diff", "--name-only", "origin/main...HEAD")
    if not diff_output:
        return []

    migrations = []
    for line in diff_output.splitlines():
        line = line.strip()
        if MIGRATION_PATTERN.search(line) and not MIGRATION_EXCLUDE.search(line):
            # Extract migration name from filename
            m = re.search(r'(\d+_\w+)\.cs$', line)
            if m:
                migrations.append(m.group(1))

    return migrations


def check_for_seeder_tables(migrations):
    """
    Heuristic: check if migration names suggest new tables that need seeding.
    Names like 'AddParkBoundaries', 'AddPointsOfInterest' etc.
    """
    seed_keywords = ['add', 'create', 'initial', 'import', 'seed']
    likely_need_seeding = []
    for name in migrations:
        # Remove timestamp prefix
        clean = re.sub(r'^\d+_', '', name)
        if any(kw in clean.lower() for kw in seed_keywords):
            likely_need_seeding.append(clean)
    return likely_need_seeding


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")

    # Only fire on gh pr create
    if not re.search(r'\bgh\s+pr\s+create\b', command, re.IGNORECASE):
        return 0

    # Only fire when targeting main
    if "--base" in command and "main" not in command:
        return 0

    migrations = get_new_migrations()
    if not migrations:
        return 0

    likely_seeding = check_for_seeder_tables(migrations)

    lines = [
        "PR MIGRATION CHECKLIST",
        "",
        f"This PR includes {len(migrations)} new EF Core migration(s):",
    ]
    for m in migrations:
        lines.append(f"  - {m}")

    lines.append("")
    lines.append("After merging and deploying, verify:")
    lines.append("  1. Migration auto-applies on app restart (check app logs)")
    lines.append("  2. New tables are created in the correct schema (roadtrip.*)")

    if likely_seeding:
        lines.append("")
        lines.append("  WARNING: These migrations likely create EMPTY tables:")
        for s in likely_seeding:
            lines.append(f"    - {s}")
        lines.append("")
        lines.append("  If the feature requires seeded data, run the seeder AFTER deploy:")
        lines.append("  WSL_SQL_CONNECTION=\"<prod conn from az CLI>\" dotnet run \\")
        lines.append("    --project src/RoadTripMap.PoiSeeder -- <flags> --confirm-remote")
        lines.append("")
        lines.append("  Get prod connection: az webapp config appsettings list \\")
        lines.append("    --name app-roadtripmap-prod --resource-group rg-roadtripmap-prod \\")
        lines.append("    --query \"[?name=='ConnectionStrings__DefaultConnection'].value\" -o tsv")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n".join(lines)
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
