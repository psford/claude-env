#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: JavaScript test theater guard.

Fires on git commit. Detects new .test.js files that define functions
at the top level but do NOT import/require the module under test.
This is the "copy-paste test" anti-pattern: production logic is copied
into the test file, so tests pass even when the real module has bugs.

Blocks commit (exit 2) when detected.
Allowlist: // COPY-FOR-TEST: annotation in the file.
           Files in __fixtures__ or test-helpers directories.
"""

import json
import sys
import re
import subprocess


FUNCTION_DEFINITION = re.compile(
    r'^(?:function\s+\w+\s*\(|const\s+\w+\s*=\s*(?:async\s+)?\(|'
    r'const\s+\w+\s*=\s*(?:async\s+)?function)',
    re.MULTILINE
)

IMPORT_OR_REQUIRE = re.compile(
    r'require\s*\(\s*[\'"][^\'"]',
    re.IGNORECASE
)

ALLOWLIST = re.compile(
    r'//\s*COPY-FOR-TEST\s*:',
    re.IGNORECASE
)

FIXTURE_PATH = re.compile(
    r'(?:__fixtures__|test-helpers|testUtils|test_utils)',
    re.IGNORECASE
)


def get_new_js_test_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                fname = parts[1]
                if fname.endswith(".test.js") or fname.endswith(".spec.js"):
                    normalized = fname.replace("\\", "/")
                    if FIXTURE_PATH.search(normalized):
                        continue
                    files.append(fname)
        return files
    except Exception:
        return []


def read_staged_content(filepath):
    try:
        result = subprocess.run(
            ["git", "show", f":{filepath}"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


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

    new_files = get_new_js_test_files()
    if not new_files:
        return 0

    violations = []
    for fpath in new_files:
        content = read_staged_content(fpath)
        if not content:
            continue

        if ALLOWLIST.search(content):
            continue

        has_imports = bool(IMPORT_OR_REQUIRE.search(content))
        if has_imports:
            continue

        matches = FUNCTION_DEFINITION.findall(content)
        if len(matches) >= 2:
            violations.append({
                "file": fpath,
                "fn_count": len(matches)
            })

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: New JS test file copies production logic instead of importing it",
        "=" * 70,
        "",
        "Tests that duplicate functions from production code give false confidence.",
        "The copy can pass while the real module has a different bug.",
        "",
    ]

    for v in violations:
        lines.append(f"File: {v['file']}")
        lines.append(f"  {v['fn_count']} top-level function definitions found, no require() imports.")
        lines.append("")

    lines += [
        "REQUIRED — choose one:",
        "  1. Export from source and require() in test:",
        "     // In source: if (typeof module !== 'undefined') module.exports = { fn };",
        "     // In test:   const { fn } = require('../js/source.js');",
        "  2. Annotate: // COPY-FOR-TEST: [reason, e.g. DOM deps prevent import]",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
