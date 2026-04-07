#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: JavaScript dead assignment guard.

Fires on git commit. Scans staged wwwroot/js/*.js files for patterns where
the result of an async call to a meaningful-return function is captured in a
`const` but never used again before the next closing brace at the same
indentation level.

Meaningful-return function name patterns:
  get, fetch, getIds, find, load, read, query, search
  (prefix or suffix match on the camelCase function name)

Skip lines annotated with // IGNORE-RETURN:

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import re
import subprocess
import sys


SOURCE_JS_PATTERN = re.compile(r'wwwroot/js/[^/]+\.js$', re.IGNORECASE)

SKIP_ANNOTATION = re.compile(r'//\s*IGNORE-RETURN\s*:', re.IGNORECASE)

# Matches: const <name> = await <fn>(  where fn is a meaningful-return function
# Meaningful: name contains get/fetch/find/load/read/query/search as a word component
MEANINGFUL_FN = re.compile(
    r'\b(?:get|fetch|find|load|read|query|search|getIds?)\w*\b',
    re.IGNORECASE
)

# Full assignment pattern: const <varname> = await <expr>(
DEAD_ASSIGN_PATTERN = re.compile(
    r'^(?P<indent>[ \t]*)const\s+(?P<varname>[A-Za-z_$][A-Za-z0-9_$]*)'
    r'\s*=\s*await\s+(?P<expr>[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*)'
    r'\s*\('
)


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args), capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_staged_js_files():
    output = run_git("diff", "--cached", "--name-only")
    return [
        f.strip()
        for f in output.splitlines()
        if f.strip() and SOURCE_JS_PATTERN.search(f.strip())
    ]


def read_staged_content(filepath):
    return run_git("show", f":{filepath}")


def is_meaningful_return_fn(fn_expr):
    """Return True if the function name (or method name) is a meaningful-return name."""
    # Get just the final method/function name component
    parts = fn_expr.split(".")
    fn_name = parts[-1]
    return bool(MEANINGFUL_FN.match(fn_name))


def check_file(fpath, content):
    """Return list of violation dicts for dead assignments in this file."""
    violations = []
    lines = content.splitlines()

    for i, raw_line in enumerate(lines):
        lineno = i + 1
        line = raw_line.rstrip()

        # Skip blank lines and full-line comments
        stripped = line.lstrip()
        if not stripped or stripped.startswith("//"):
            continue

        # Skip annotated lines
        if SKIP_ANNOTATION.search(line):
            continue

        m = DEAD_ASSIGN_PATTERN.match(line)
        if not m:
            continue

        indent = m.group("indent")
        varname = m.group("varname")
        fn_expr = m.group("expr")

        # Only check meaningful-return functions
        if not is_meaningful_return_fn(fn_expr):
            continue

        # Scan forward from the next line until we hit a closing brace
        # at the same (or shallower) indentation level, collecting usage of varname
        closing_brace_pattern = re.compile(
            r'^' + re.escape(indent) + r'\}'
        )
        # varname usage: appears as a whole identifier (not in comments)
        var_usage_pattern = re.compile(
            r'(?<![A-Za-z0-9_$])' + re.escape(varname) + r'(?![A-Za-z0-9_$])'
        )

        used = False
        found_close = False

        for j in range(i + 1, len(lines)):
            subsequent = lines[j].rstrip()
            substripped = subsequent.lstrip()

            # Skip full-line comments when checking usage
            if not substripped.startswith("//"):
                # Strip inline comment before checking usage
                code_part = re.split(r'//(?!.*[\'"])', subsequent)[0]
                if var_usage_pattern.search(code_part):
                    used = True
                    break

            # Check if we've hit the closing brace at same indent
            if closing_brace_pattern.match(subsequent):
                found_close = True
                break

        # Only flag if we found a closing brace without the variable being used
        if found_close and not used:
            violations.append({
                "file": fpath,
                "line": lineno,
                "varname": varname,
                "fn": fn_expr,
                "text": line.strip()[:120],
            })

    return violations


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

    staged_js = get_staged_js_files()
    if not staged_js:
        return 0

    all_violations = []
    for fpath in staged_js:
        content = read_staged_content(fpath)
        if not content:
            continue
        all_violations.extend(check_file(fpath, content))

    if not all_violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: Dead assignment detected in JavaScript",
        "=" * 70,
        "",
        "These async calls return meaningful data that is never used.",
        "A dead assignment usually means the result was forgotten,",
        "causing silent data loss or skipped error handling.",
        "",
    ]

    for v in all_violations:
        lines.append(f"  {v['file']}:{v['line']}  [const {v['varname']} = await {v['fn']}(...)]")
        lines.append(f"    Code:    {v['text']}")
        lines.append(f"    Issue:   '{v['varname']}' is never referenced before the block closes.")
        lines.append("")

    lines += [
        "To resolve:",
        "  - Use the return value (pass it to another function, log it, return it).",
        "  - If the call is intentionally fire-and-forget, rewrite without const:",
        "      await fn();",
        "  - To suppress a false positive, annotate the line:",
        "      const x = await fn(); // IGNORE-RETURN: reason",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
