#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Stale path guard.

Fires on git commit. Reads staged diff and blocks (exit 2) if any added line
in scanned file types matches a stale-path pattern from stale_path_patterns.json.

Escape hatch: add a comment containing  # STALE-PATH-OK: <reason>  on the
same line or the line immediately following the offending line. This tells the
guard the reference is intentional and should not be blocked.

Fails open (exits 0) if the patterns file is missing.
"""

import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PATTERNS_FILE = os.path.join(REPO_ROOT, ".claude", "stale_path_patterns.json")

SCANNED_EXTENSIONS = re.compile(
    r'\.(md|yml|yaml|json|cs|py|sh|ps1|csproj|sln|xml|html|js|ts|bicep)$',
    re.IGNORECASE,
)

ESCAPE_HATCH = re.compile(r'#\s*STALE-PATH-OK\s*:', re.IGNORECASE)


def load_patterns():
    """Load patterns from JSON file. Returns None if file is missing."""
    if not os.path.exists(PATTERNS_FILE):
        return None
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("patterns", [])
    except (json.JSONDecodeError, OSError):
        return None


def get_staged_diff():
    """Return the staged diff as a string, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0"],
            capture_output=True, text=True, timeout=15,
            cwd=REPO_ROOT,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def parse_diff_additions(diff_text):
    """
    Parse unified diff and return a list of (filename, line_number, line_content)
    for every added line in a scanned file type.
    """
    additions = []
    current_file = None
    current_line = 0

    for raw_line in diff_text.split("\n"):
        # Track which file we're in
        if raw_line.startswith("+++ b/"):
            path = raw_line[6:].strip()
            if SCANNED_EXTENSIONS.search(path):
                current_file = path
            else:
                current_file = None
            current_line = 0
            continue

        if raw_line.startswith("--- "):
            continue

        # Hunk header: @@ -old_start,old_count +new_start,new_count @@
        if raw_line.startswith("@@"):
            m = re.search(r'\+(\d+)', raw_line)
            if m:
                current_line = int(m.group(1)) - 1
            continue

        if current_file is None:
            continue

        if raw_line.startswith("+"):
            current_line += 1
            additions.append((current_file, current_line, raw_line[1:]))
        elif not raw_line.startswith("-"):
            current_line += 1

    return additions


def check_violations(additions, patterns):
    """
    Check additions against patterns.
    Returns list of (filename, line_number, line_content, pattern_entry) for violations.
    Respects the STALE-PATH-OK escape hatch on the same line.
    """
    compiled = []
    for p in patterns:
        try:
            compiled.append((re.compile(p["pattern"]), p))
        except re.error:
            # Skip malformed patterns — fail open
            continue

    violations = []
    lines_by_file = {}
    for fname, lineno, content in additions:
        lines_by_file.setdefault(fname, {})[lineno] = content

    for fname, lineno, content in additions:
        # Check escape hatch on this line
        if ESCAPE_HATCH.search(content):
            continue

        for compiled_re, pattern_entry in compiled:
            if compiled_re.search(content):
                violations.append((fname, lineno, content, pattern_entry))
                break  # One violation per line is enough

    return violations


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = hook_input.get("tool_input", {}).get("command", "")
    # Only fire on git commit commands
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        sys.exit(0)

    patterns = load_patterns()
    if patterns is None:
        # Fail open — patterns file missing
        sys.exit(0)

    diff = get_staged_diff()
    if not diff:
        sys.exit(0)

    additions = parse_diff_additions(diff)
    violations = check_violations(additions, patterns)

    if not violations:
        sys.exit(0)

    # Group violations by file
    by_file = {}
    for fname, lineno, content, pattern_entry in violations:
        by_file.setdefault(fname, []).append((lineno, content, pattern_entry))

    lines = [
        "STALE PATH DETECTED — commit blocked.",
        "",
        "The staged diff contains references to claudeProjects monorepo paths.",
        "These paths must not appear in the standalone claude-env repo.",
        "",
    ]
    for fname in sorted(by_file):
        lines.append(f"  {fname}:")
        for lineno, content, pattern_entry in by_file[fname]:
            lines.append(f"    Line {lineno}: {content.rstrip()}")
            lines.append(f"    Pattern : {pattern_entry['pattern']}")
            lines.append(f"    Remedy  : {pattern_entry['remedy']}")
            lines.append("")

    lines += [
        "To suppress a specific instance (if intentional), add to that line:",
        "    # STALE-PATH-OK: <reason>",
        "",
        "To re-scan the full working tree:",
        "    python helpers/scan_stale_paths.py",
    ]

    output = {
        "decision": "block",
        "reason": "\n".join(lines),
    }
    print(json.dumps(output))
    sys.exit(2)


if __name__ == "__main__":
    main()
