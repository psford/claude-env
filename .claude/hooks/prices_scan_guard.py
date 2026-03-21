#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Prices table full-scan guard.

Fires on git commit. Scans staged diff for newly added code that introduces
data.Prices table scans — the root cause of 12 DTU exhaustion incidents on
Azure SQL Basic tier (5 DTU / 60 workers).

Blocks commit (exit 2) when detected.

BLOCKED patterns (cause full table scan or high DTU):
  - COUNT(*) on Prices without SecurityAlias filter
  - SELECT DISTINCT on Prices
  - GROUP BY on Prices without SecurityAlias in the key
  - .CountAsync()/.ToListAsync()/.SumAsync() on _context.Prices without Where

SAFE patterns (suppressed):
  - WHERE SecurityAlias = @x
  - SecurityPriceCoverage / CoverageSummary references
  - TOP 1 ORDER BY
  - // DTU-OK: or -- DTU-OK: annotation
"""

import json
import sys
import re
import subprocess


SQL_DANGEROUS = [
    (re.compile(r'COUNT\s*\(\s*\*\s*\).*FROM\s+(?:\[?data\]?\.)?\[?Prices\]?\b', re.IGNORECASE),
     "COUNT(*) on Prices without SecurityAlias filter — use SecurityPriceCoverage"),

    (re.compile(r'SELECT\s+DISTINCT.*FROM\s+(?:\[?data\]?\.)?\[?Prices\]?\b', re.IGNORECASE),
     "SELECT DISTINCT on Prices — use pre-aggregated coverage tables"),

    (re.compile(r'FROM\s+(?:\[?data\]?\.)?\[?Prices\]?\b.*GROUP\s+BY', re.IGNORECASE),
     "GROUP BY on Prices — aggregation over full table exhausts DTU"),
]

LINQ_DANGEROUS = [
    (re.compile(r'_context\.Prices\s*\.(?:AsNoTracking\(\)\s*\.)?CountAsync\s*\(\s*\)', re.IGNORECASE),
     ".CountAsync() on full Prices set — use SecurityPriceCoverage"),

    (re.compile(r'_context\.Prices\s*\.(?:AsNoTracking\(\)\s*\.)?ToListAsync\s*\(\s*\)', re.IGNORECASE),
     "Unbounded .ToListAsync() on Prices — filter by SecurityAlias first"),

    (re.compile(r'_context\.Prices\s*\.(?:AsNoTracking\(\)\s*\.)?SumAsync\s*\(', re.IGNORECASE),
     ".SumAsync() on Prices — use coverage tables for aggregation"),
]

SAFE_INDICATORS = re.compile(
    r'SecurityAlias\s*==|SecurityPriceCoverage|CoverageSummary|TOP\s+1|'
    r'//\s*DTU-OK:|--\s*DTU-OK:|SecurityPriceCoverageByYear|'
    r'WHERE.*SecurityAlias|\.Where\(.*SecurityAlias',
    re.IGNORECASE
)


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=5"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def parse_added_lines(diff_text):
    results = []
    current_file = None
    lineno = 0

    for i, line in enumerate(diff_text.split("\n")):
        if line.startswith("diff --git"):
            current_file = None
        elif line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            m = re.search(r'\+(\d+)', line)
            if m:
                lineno = int(m.group(1)) - 1
        elif current_file:
            if line.startswith("+") and not line.startswith("+++"):
                lineno += 1
                # Only check C# and SQL files
                ext = current_file.rsplit(".", 1)[-1].lower() if "." in current_file else ""
                if ext in ("cs", "sql"):
                    # Gather surrounding context for safe-pattern detection
                    all_lines = diff_text.split("\n")
                    ctx_start = max(0, i - 5)
                    ctx_end = min(len(all_lines), i + 6)
                    context = "\n".join(all_lines[ctx_start:ctx_end])
                    results.append((current_file, lineno, line[1:], context))
            elif not line.startswith("-"):
                lineno += 1

    return results


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    diff = get_staged_diff()
    if not diff:
        return 0

    added_lines = parse_added_lines(diff)
    violations = []

    for filename, lineno, content, context in added_lines:
        stripped = content.strip()
        if stripped.startswith("//") or stripped.startswith("--") or stripped.startswith("*"):
            continue

        # Check SQL patterns
        for pattern, message in SQL_DANGEROUS:
            if pattern.search(content):
                if not SAFE_INDICATORS.search(context):
                    violations.append({
                        "file": filename, "line": lineno,
                        "content": stripped[:120], "reason": message,
                    })

        # Check LINQ patterns
        for pattern, message in LINQ_DANGEROUS:
            if pattern.search(content):
                if not SAFE_INDICATORS.search(context):
                    violations.append({
                        "file": filename, "line": lineno,
                        "content": stripped[:120], "reason": message,
                    })

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: Prices table full-scan pattern detected",
        "Azure SQL Basic = 5 DTU. This pattern has caused 12 DTU incidents.",
        "=" * 70,
        "",
    ]

    for v in violations:
        lines.append(f"  {v['file']}:{v['line']}")
        lines.append(f"  Code:   {v['content']}")
        lines.append(f"  Issue:  {v['reason']}")
        lines.append("")

    lines += [
        "ALTERNATIVES:",
        "  COUNT/SUM  -> use data.SecurityPriceCoverage or data.CoverageSummary",
        "  DISTINCT   -> use skip-scan pattern (GetDistinctDatesAsync)",
        "  GROUP BY   -> include SecurityAlias in the GROUP BY key",
        "  ToListAsync-> add .Where(p => p.SecurityAlias == alias) first",
        "",
        "If known-safe, add: // DTU-OK: bounded by SecurityAlias index seek",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
