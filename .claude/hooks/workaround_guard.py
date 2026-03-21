#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Workaround-instead-of-root-cause-fix guard.

Fires on git commit. Scans staged diff for two workaround smells:
1. New Python file in helpers/scripts/ duplicating C# business logic
2. C# hard-cap (Math.Min, Math.Clamp) at sentinel values without diagnostic comment

Blocks commit (exit 2) when detected.
Allowlist: lines with "# WORKAROUND:" or "// Root cause:" comments.
"""

import json
import sys
import re
import subprocess


PYTHON_LOGIC_SMELLS = re.compile(
    r'ImportanceScore|importance_score|coverage.*percent|percent.*coverage|'
    r'price_count|PriceCount|heatmap.*intensit|intensit.*heatmap|'
    r'SecurityAlias|security_alias|expected_count|ExpectedCount',
    re.IGNORECASE
)

CSHARP_CAP_PATTERNS = re.compile(
    r'Math\.Min\s*\([^,]+,\s*(?:100|1\.0|1f|100\.0|100f)\s*\)|'
    r'Math\.Clamp\s*\([^,]+,|'
    r'if\s*\(.+?>\s*(?:100|1\.0|1f)\s*\)\s*\{?\s*\w+\s*=\s*(?:100|1\.0|1f)',
    re.IGNORECASE
)

# Check 3: JS display-layer caps that mask data issues
JS_CAP_PATTERNS = re.compile(
    r'Math\.min\s*\([^,]+,\s*(?:100|1\.0|1)\s*\)|'
    r'Math\.max\s*\(\s*(?:0)\s*,\s*Math\.min\s*\(|'
    r'>\s*(?:100|1\.0)\s*\?\s*["\x27]?>?\s*100|'
    r'\.clamp\s*\(|'
    r'if\s*\([^)]*>\s*(?:100|1\.0)\s*\)\s*\{?\s*\w+\s*=\s*(?:100|1\.0)',
    re.IGNORECASE
)

INTENTIONAL_COMMENT = re.compile(
    r'(?://|#).*(?:root\s+cause|TODO|FIXME|tracked|#\d+|by\s+design|known\s+issue|WORKAROUND)',
    re.IGNORECASE
)


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=3"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def parse_diff_sections(diff_text):
    sections = []
    current = None
    lineno = 0

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current:
                sections.append(current)
            current = {"filename": "", "added_lines": [], "context_lines": []}
            lineno = 0
        elif line.startswith("+++ b/") and current is not None:
            current["filename"] = line[6:]
        elif line.startswith("@@") and current is not None:
            m = re.search(r'\+(\d+)', line)
            if m:
                lineno = int(m.group(1)) - 1
        elif current is not None:
            if line.startswith("+") and not line.startswith("+++"):
                lineno += 1
                current["added_lines"].append((lineno, line[1:]))
            elif line.startswith("-"):
                pass
            else:
                lineno += 1
                current["context_lines"].append(line)

    if current:
        sections.append(current)

    return sections


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

    sections = parse_diff_sections(diff)
    violations = []

    for section in sections:
        fname = section["filename"]

        # Check 1: Python business logic duplication
        if fname.endswith(".py") and any(d in fname for d in ["helpers/", "scripts/"]):
            smell_lines = []
            for lineno, content in section["added_lines"]:
                if INTENTIONAL_COMMENT.search(content):
                    continue
                if PYTHON_LOGIC_SMELLS.search(content):
                    smell_lines.append((lineno, content.strip()))

            if smell_lines:
                violations.append({
                    "type": "python_duplicate",
                    "file": fname,
                    "lines": smell_lines[:3],
                })

        # Check 2: C# hard-cap without diagnosis
        if fname.endswith(".cs"):
            for lineno, content in section["added_lines"]:
                if not CSHARP_CAP_PATTERNS.search(content):
                    continue
                if INTENTIONAL_COMMENT.search(content):
                    continue

                # Check adjacent added lines for diagnostic comment
                adjacent_lines = [c for ln, c in section["added_lines"]
                                  if abs(ln - lineno) <= 2]
                adjacent_text = "\n".join(adjacent_lines)
                if INTENTIONAL_COMMENT.search(adjacent_text):
                    continue

                violations.append({
                    "type": "csharp_cap",
                    "file": fname,
                    "line": lineno,
                    "content": content.strip()[:120],
                })

        # Check 3: JS display-layer caps in UI files
        if fname.endswith(".js") and any(d in fname for d in [
            "wwwroot/", "components/", "views/", "src/StockAnalyzer.Api/wwwroot"
        ]):
            for lineno, content in section["added_lines"]:
                if not JS_CAP_PATTERNS.search(content):
                    continue
                if INTENTIONAL_COMMENT.search(content):
                    continue

                adjacent_lines = [c for ln, c in section["added_lines"]
                                  if abs(ln - lineno) <= 2]
                adjacent_text = "\n".join(adjacent_lines)
                if INTENTIONAL_COMMENT.search(adjacent_text):
                    continue

                violations.append({
                    "type": "js_cap",
                    "file": fname,
                    "line": lineno,
                    "content": content.strip()[:120],
                })

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: Workaround pattern detected — diagnose root cause first",
        "=" * 70,
        "",
    ]

    for v in violations:
        if v["type"] == "python_duplicate":
            lines.append(f"PYTHON LOGIC DUPLICATION: {v['file']}")
            lines.append("  Re-implements C# business logic in Python.")
            lines.append("  Workaround scripts leave the original bug open.")
            for ln, content in v["lines"]:
                lines.append(f"    L{ln}: {content[:100]}")
            lines.append("")
            lines.append("  FIX: Identify the C# method, fix it there. Delete the script.")
        elif v["type"] == "csharp_cap":
            lines.append(f"HARD CAP WITHOUT DIAGNOSIS: {v['file']}:{v['line']}")
            lines.append(f"  {v['content']}")
            lines.append("  Capping suppresses a symptom. The data issue remains.")
            lines.append("")
            lines.append("  FIX: Diagnose WHY the value exceeds range, or add:")
            lines.append("    // Root cause: [explanation] — tracked in #NNN")
        elif v["type"] == "js_cap":
            lines.append(f"JS DISPLAY CAP WITHOUT DIAGNOSIS: {v['file']}:{v['line']}")
            lines.append(f"  {v['content']}")
            lines.append("  Display-layer capping hides data issues from users.")
            lines.append("")
            lines.append("  FIX: Diagnose WHY the value exceeds range, or add:")
            lines.append("    // Root cause: [explanation] — tracked in #NNN")

        lines.append("")

    lines.append("If intentional, add: # WORKAROUND: root cause is [X], tracked in #NNN")
    lines.append("=" * 70)

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
