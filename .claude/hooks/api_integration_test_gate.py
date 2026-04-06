#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: API integration test gate.

Fires on git commit. When staged files include importer source files
(anything under */Importers/*.cs or */Seeder/*Importer*.cs), runs the
live PAD-US integration test. If the test fails or the API is unreachable,
the commit is blocked.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import os
import re
import subprocess
import sys

def get_repo_root():
    """Get the git repo root of the project being committed to."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None

def get_test_project():
    """Resolve test project path relative to repo root."""
    root = get_repo_root()
    if not root:
        return None
    return os.path.join(root, "tests", "RoadTripMap.Tests", "RoadTripMap.Tests.csproj")

IMPORTER_PATTERNS = [
    re.compile(r".*/Importers/[^/]+\.cs$"),
    re.compile(r".*/Seeder/[^/]*Importer[^/]*\.cs$"),
]

INTEGRATION_TIMEOUT = 120  # seconds (live API can be slow)


def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        return []


def has_importer_files(staged_files):
    for fpath in staged_files:
        normalized = fpath.replace("\\", "/")
        for pattern in IMPORTER_PATTERNS:
            if pattern.search(normalized):
                return True
    return False


def run_integration_test():
    """
    Runs the integration test suite with RUN_INTEGRATION_TESTS=1.
    Returns (success: bool, output: str).
    """
    env = os.environ.copy()
    env["RUN_INTEGRATION_TESTS"] = "1"

    cmd = [
        "dotnet", "test",
        "--filter", "Category=Integration",
        "--project", get_test_project(),
        "--no-build",
        "--configuration", "Release",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=INTEGRATION_TIMEOUT,
            env=env,
        )
        combined = result.stdout + "\n" + result.stderr
        return result.returncode == 0, combined
    except subprocess.TimeoutExpired:
        return False, f"Integration test timed out after {INTEGRATION_TIMEOUT}s."
    except FileNotFoundError:
        return False, "dotnet not found. Ensure .NET SDK is installed."
    except Exception as e:
        return False, f"Unexpected error running integration test: {e}"


def needs_build():
    """
    Check whether the test project has been built in Release configuration.
    Returns True if a build is needed.
    """
    root = get_repo_root()
    if not root:
        return True
    dll_path = os.path.join(
        root, "tests", "RoadTripMap.Tests",
        "bin", "Release", "net8.0", "RoadTripMap.Tests.dll"
    )
    return not os.path.exists(dll_path)


def run_build():
    """
    Builds the test project. Returns (success: bool, output: str).
    """
    cmd = [
        "dotnet", "build",
        get_test_project(),
        "--configuration", "Release",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=120,
        )
        combined = result.stdout + "\n" + result.stderr
        return result.returncode == 0, combined
    except subprocess.TimeoutExpired:
        return False, "dotnet build timed out after 120s."
    except FileNotFoundError:
        return False, "dotnet not found. Ensure .NET SDK is installed."
    except Exception as e:
        return False, f"Unexpected error during build: {e}"


def is_network_error(output):
    """
    Heuristically detect whether the test failure is a network/API issue.
    """
    network_hints = [
        "HttpRequestException",
        "SocketException",
        "No such host",
        "Connection refused",
        "Network is unreachable",
        "Unable to connect",
        "SSL",
        "timeout",
        "edits.nationalmap.gov",
    ]
    lower_output = output.lower()
    return any(hint.lower() in lower_output for hint in network_hints)


def block(message, test_output=""):
    lines = [
        "",
        "=" * 70,
        "BLOCKED: API integration test gate",
        "=" * 70,
        "",
        message,
    ]
    if test_output:
        lines += [
            "",
            "--- Test output ---",
            test_output.strip()[-3000:],  # Trim to last 3000 chars to avoid flooding
            "--- End test output ---",
        ]
    lines += [
        "",
        "Fix the importer or the live API issue before committing.",
        "=" * 70,
    ]
    print("\n".join(lines), file=sys.stderr)
    return 2


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

    staged_files = get_staged_files()
    if not has_importer_files(staged_files):
        return 0

    importer_files = [
        f for f in staged_files
        if any(p.search(f.replace("\\", "/")) for p in IMPORTER_PATTERNS)
    ]
    print(
        f"[api_integration_test_gate] Importer files staged: {importer_files}",
        file=sys.stderr
    )
    print(
        "[api_integration_test_gate] Running live PAD-US integration test...",
        file=sys.stderr
    )

    if needs_build():
        print(
            "[api_integration_test_gate] Test project not built — building now...",
            file=sys.stderr
        )
        build_ok, build_output = run_build()
        if not build_ok:
            return block(
                "Build failed before integration test could run.",
                build_output
            )

    success, output = run_integration_test()

    if success:
        print(
            "[api_integration_test_gate] Integration test passed. Commit allowed.",
            file=sys.stderr
        )
        return 0

    if is_network_error(output):
        return block(
            "The live PAD-US API appears to be unreachable.\n"
            "The integration test could not connect to edits.nationalmap.gov.\n"
            "Check your network connection and try again.",
            output
        )

    return block(
        "The live PAD-US integration test FAILED.\n"
        "The importer returned unexpected results from the real API.\n"
        "Fix the importer code before committing.",
        output
    )


if __name__ == "__main__":
    sys.exit(main())
