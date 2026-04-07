#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Browser compatibility guard.

Fires on git commit. When staged wwwroot/js/*.js files contain
Node.js-only APIs, blocks the commit (exit 2).

Blocked APIs:
  setImmediate / clearImmediate
  process.env / process.argv
  __dirname / __filename
  Buffer.from / Buffer.alloc
  require('...')
  module.exports

Skip lines annotated with // BROWSER-COMPAT: or that contain typeof guards.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import re
import subprocess
import sys


SOURCE_JS_PATTERN = re.compile(r'wwwroot/js/[^/]+\.js$', re.IGNORECASE)

SKIP_ANNOTATION = re.compile(r'//\s*BROWSER-COMPAT\s*:', re.IGNORECASE)

# typeof guard: typeof process !== 'undefined', typeof require === 'function', etc.
TYPEOF_GUARD = re.compile(r'\btypeof\s+(?:process|require|module|Buffer|__dirname|__filename)\b')

# Each entry: (regex, api_name, browser_alternative)
NODE_ONLY_APIS = [
    (
        re.compile(r'\bsetImmediate\s*\('),
        "setImmediate",
        "setTimeout(fn, 0)"
    ),
    (
        re.compile(r'\bclearImmediate\s*\('),
        "clearImmediate",
        "clearTimeout()"
    ),
    (
        re.compile(r'\bprocess\.env\b'),
        "process.env",
        "inject config via data attributes or a /config endpoint"
    ),
    (
        re.compile(r'\bprocess\.argv\b'),
        "process.argv",
        "parse URL params with URLSearchParams or pass config explicitly"
    ),
    (
        re.compile(r'\b__dirname\b'),
        "__dirname",
        "use import.meta.url with URL() for ESM, or remove path logic"
    ),
    (
        re.compile(r'\b__filename\b'),
        "__filename",
        "use import.meta.url for ESM, or remove path logic"
    ),
    (
        re.compile(r'\bBuffer\.from\s*\('),
        "Buffer.from",
        "TextEncoder / TextDecoder or btoa() / atob()"
    ),
    (
        re.compile(r'\bBuffer\.alloc\s*\('),
        "Buffer.alloc",
        "new Uint8Array(n) or new ArrayBuffer(n)"
    ),
    (
        re.compile(r'\brequire\s*\(\s*[\'"]'),
        "require('...')",
        "ES module import or a bundled dependency"
    ),
    (
        re.compile(r'\bmodule\.exports\b'),
        "module.exports",
        "export keyword (ES module syntax)"
    ),
]


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


def check_file(fpath, content):
    """Return list of violation dicts for this file."""
    violations = []
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.rstrip()

        # Skip blank lines and comment-only lines
        stripped = line.lstrip()
        if not stripped or stripped.startswith("//"):
            continue

        # Skip lines with the bypass annotation
        if SKIP_ANNOTATION.search(line):
            continue

        # Skip lines that contain typeof guards (checking for the presence at runtime)
        if TYPEOF_GUARD.search(line):
            continue

        for pattern, api_name, alternative in NODE_ONLY_APIS:
            if pattern.search(line):
                violations.append({
                    "file": fpath,
                    "line": lineno,
                    "api": api_name,
                    "alternative": alternative,
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
        "BLOCKED: Node.js-only API detected in browser JS",
        "=" * 70,
        "",
        "These APIs are unavailable in browsers. They will cause runtime errors.",
        "",
    ]

    for v in all_violations:
        lines.append(f"  {v['file']}:{v['line']}  [{v['api']}]")
        lines.append(f"    Code:        {v['text']}")
        lines.append(f"    Alternative: {v['alternative']}")
        lines.append("")

    lines += [
        "To suppress a false positive, annotate the line:",
        "  someCall(); // BROWSER-COMPAT: reason this is safe",
        "",
        "Lines containing typeof guards are skipped automatically.",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
