#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Plan-config drift guard.

Fires on git commit. Scans staged diff for two anti-patterns:
1. EXISTENCE-ONLY VERIFICATION in test/verify scripts
2. PLACEHOLDER .py files committed to hook directories

Allowlist: # EXISTENCE-CHECK-OK: reason  or  # PLACEHOLDER-OK: reason
"""

import json
import sys
import re
import subprocess


EXISTENCE_CHECK_PATTERNS = re.compile(
    r'(?:'
    r'test\s+-[fdes]\s+["\']?~?[\$\{]?HOME|'
    r'test\s+-[fdes]\s+.*\.json|'
    r'test\s+-[fdes]\s+.*settings|'
    r'os\.path\.exists\s*\(["\'].*(?:json|settings|plugin|hooks?|installed)["\']|'
    r'\btest -f\b.*(?:plugin|hook|settings|installed|memory|MEMORY)'
    r')',
    re.IGNORECASE
)

BEHAVIORAL_GUARDS = re.compile(
    r'(?:'
    r'json\.load|json\.loads|python3.*-c.*json|'
    r'grep\s+-q|jq\s+\.|'
    r'command\s+-v|which\s+|claude\s+--version|'
    r'installPath.*exist|resolv'
    r')',
    re.IGNORECASE
)

SHEBANG_RE = re.compile(r'^#!')
COMMENT_RE = re.compile(r'^\s*#')
BLANK_RE = re.compile(r'^\s*$')
INTENTIONAL_EXISTENCE = re.compile(r'#\s*EXISTENCE-CHECK-OK\s*:', re.IGNORECASE)
INTENTIONAL_PLACEHOLDER = re.compile(r'#\s*PLACEHOLDER-OK\s*:', re.IGNORECASE)


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=5"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_staged_file_contents(filepath):
    try:
        result = subprocess.run(
            ["git", "show", f":{filepath}"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_staged_python_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        return [f for f in result.stdout.strip().splitlines() if f.endswith(".py")]
    except Exception:
        return []


def is_placeholder(content):
    lines = content.splitlines()
    real_lines = [
        ln for ln in lines
        if not SHEBANG_RE.match(ln)
        and not COMMENT_RE.match(ln)
        and not BLANK_RE.match(ln)
    ]
    return len(real_lines) < 3


def parse_diff_added_lines(diff_text):
    files = {}
    current = None
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current = line[6:]
            files[current] = []
        elif current and line.startswith("+") and not line.startswith("+++"):
            files[current].append(line[1:])
    return files


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

    violations = []

    added_by_file = parse_diff_added_lines(diff)
    for fname, added_lines in added_by_file.items():
        if not any(kw in fname.lower() for kw in
                   ["verify", "test", "check", "setup", "validate", "ac-"]):
            continue
        for lineno, content in enumerate(added_lines, 1):
            if INTENTIONAL_EXISTENCE.search(content):
                continue
            if not EXISTENCE_CHECK_PATTERNS.search(content):
                continue
            window = added_lines[max(0, lineno - 5):lineno + 5]
            window_text = "\n".join(window)
            if BEHAVIORAL_GUARDS.search(window_text):
                continue
            violations.append({
                "type": "existence_only",
                "file": fname,
                "line": lineno,
                "content": content.strip()[:120],
            })

    staged_py = get_staged_python_files()
    for fpath in staged_py:
        if ".claude/hooks/" not in fpath and "hooks/" not in fpath:
            continue
        content = get_staged_file_contents(fpath)
        if not content:
            continue
        if INTENTIONAL_PLACEHOLDER.search(content):
            continue
        if is_placeholder(content):
            violations.append({"type": "placeholder_hook", "file": fpath})

    if not violations:
        return 0

    lines = ["", "BLOCKED: Plan-config drift detected", "=" * 50, ""]
    for v in violations:
        if v["type"] == "existence_only":
            lines.append(f"EXISTENCE-ONLY CHECK: {v['file']} line {v['line']}")
            lines.append(f"  {v['content']}")
            lines.append("  Add a behavioral check (json.load, grep -q, etc.) or annotate:")
            lines.append("    # EXISTENCE-CHECK-OK: reason")
            lines.append("")
        elif v["type"] == "placeholder_hook":
            lines.append(f"PLACEHOLDER HOOK: {v['file']}")
            lines.append("  File has no real code. Implement it or annotate:")
            lines.append("    # PLACEHOLDER-OK: reason")
            lines.append("")

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
