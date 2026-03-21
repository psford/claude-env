#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Mock-only test guard.

Fires on git commit. Detects new C# test files that use only mocks
(Mock<T>, Substitute.For<T>) without constructing real objects.
Pure mock tests give false confidence — they validate wiring, not behavior.

Blocks commit (exit 2) when detected.
Allowlist: // MOCK-ONLY: annotation, files in /Unit/ directories.
"""

import json
import sys
import re
import subprocess


MOCK_PATTERNS = re.compile(
    r'new\s+Mock\s*<|Substitute\.For\s*<|MockRepository\.',
    re.IGNORECASE
)

REAL_INSTANTIATION_PATTERNS = re.compile(
    r'new\s+\w+(?:Service|Repository|Controller|Handler|Manager)\s*\(|'
    r'WebApplicationFactory|ServiceCollection\(\)|builder\.Services|'
    r'SqliteConnection|UseInMemoryDatabase|CreateClient\(\)',
    re.IGNORECASE
)

ALLOWLIST_PATTERN = re.compile(r'//\s*MOCK-ONLY\s*:', re.IGNORECASE)


def get_new_test_files():
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
                fname_lower = fname.lower()
                if ("test" in fname_lower or "spec" in fname_lower) and fname.endswith(".cs"):
                    normalized = fname.replace("\\", "/")
                    if "/unit/" in normalized.lower():
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

    new_test_files = get_new_test_files()
    if not new_test_files:
        return 0

    violations = []
    for fpath in new_test_files:
        content = read_staged_content(fpath)
        if not content:
            continue

        if ALLOWLIST_PATTERN.search(content):
            continue

        has_mocks = bool(MOCK_PATTERNS.search(content))
        if not has_mocks:
            continue

        has_real = bool(REAL_INSTANTIATION_PATTERNS.search(content))
        if has_real:
            continue

        # Extract test subject names
        subjects = re.findall(r'class\s+(\w+?)(?:Tests?|Spec)\b', content, re.IGNORECASE)
        violations.append({"file": fpath, "subjects": subjects})

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: New test file uses only mocks — production code not exercised",
        "=" * 70,
        "",
        "Pure mock tests validate wiring, NOT that production code works.",
        "This project has had test rewrites because mock tests gave false confidence.",
        "",
    ]

    for v in violations:
        lines.append(f"File: {v['file']}")
        if v["subjects"]:
            lines.append(f"  Subject(s): {', '.join(v['subjects'])}")
        lines.append("  No real object instantiation found. No // MOCK-ONLY: annotation.")
        lines.append("")

    lines += [
        "REQUIRED — choose one:",
        "  1. Construct the real SUT: var sut = new RateLimiter(realDep);",
        "     Or use WebApplicationFactory / in-memory DB for integration.",
        "  2. Annotate: // MOCK-ONLY: [reason why mocks are appropriate]",
        "  3. Move pure unit tests to a /Unit/ subdirectory.",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
