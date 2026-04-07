#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Plan API URL guard.

Fires on git commit. When NEWLY ADDED markdown files in
docs/implementation-plans/ or docs/design-plans/ contain external API
URLs (ArcGIS, nationalmap.gov, usgs.gov/arcgis, developer.nps.gov/api,
overpass-api.de), the commit is blocked unless:

  - The file contains an <!-- API-VERIFIED: ... --> annotation, OR
  - The file contains an <!-- API-URL-UNVERIFIED-OK: ... --> annotation, OR
  - A corresponding docs/api-contracts/*.json contract file exists.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import os
import re
import subprocess
import sys


PLAN_PATHS = re.compile(
    r'^docs/(?:implementation-plans|design-plans)/[^/]+\.md$',
    re.IGNORECASE
)

EXTERNAL_API_PATTERNS = [
    re.compile(r'https?://[^\s"\'<>]*arcgis[^\s"\'<>]*', re.IGNORECASE),
    re.compile(r'https?://[^\s"\'<>]*nationalmap\.gov[^\s"\'<>]*', re.IGNORECASE),
    re.compile(r'https?://[^\s"\'<>]*usgs\.gov/arcgis[^\s"\'<>]*', re.IGNORECASE),
    re.compile(r'https?://[^\s"\'<>]*developer\.nps\.gov/api[^\s"\'<>]*', re.IGNORECASE),
    re.compile(r'https?://[^\s"\'<>]*overpass-api\.de[^\s"\'<>]*', re.IGNORECASE),
]

API_VERIFIED_ANNOTATION = re.compile(
    r'<!--\s*API-VERIFIED\s*:', re.IGNORECASE
)
API_UNVERIFIED_OK_ANNOTATION = re.compile(
    r'<!--\s*API-URL-UNVERIFIED-OK\s*:', re.IGNORECASE
)


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args), capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_newly_added_plan_files():
    """Return list of (filepath, status) for newly added plan markdown files."""
    output = run_git("diff", "--cached", "--name-status")
    results = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, fpath = parts[0].strip(), parts[1].strip()
        # Only newly added files (status starts with A)
        if status.startswith("A") and PLAN_PATHS.match(fpath):
            results.append(fpath)
    return results


def read_staged_content(filepath):
    return run_git("show", f":{filepath}")


def find_api_urls(content):
    """Return list of (lineno, url) tuples for external API URLs found."""
    hits = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        for pattern in EXTERNAL_API_PATTERNS:
            match = pattern.search(line)
            if match:
                hits.append((lineno, match.group(0)))
    return hits


def api_contract_exists(filepath):
    """
    Check whether a docs/api-contracts/*.json file exists for this plan.
    Strategy: any .json under docs/api-contracts/ in the repo counts.
    This is intentionally broad — the plan author is responsible for naming.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return False
        repo_root = result.stdout.strip()
        contracts_dir = os.path.join(repo_root, "docs", "api-contracts")
        if not os.path.isdir(contracts_dir):
            # Also check staged index for the contracts dir
            staged = run_git("diff", "--cached", "--name-only")
            return any(
                f.startswith("docs/api-contracts/") and f.endswith(".json")
                for f in staged.splitlines()
            )
        # Any json file in contracts dir is sufficient
        return any(
            f.endswith(".json")
            for f in os.listdir(contracts_dir)
        )
    except Exception:
        return False


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

    newly_added = get_newly_added_plan_files()
    if not newly_added:
        return 0

    violations = []

    for fpath in newly_added:
        content = read_staged_content(fpath)
        if not content:
            continue

        api_urls = find_api_urls(content)
        if not api_urls:
            continue

        # Check suppression options
        if API_VERIFIED_ANNOTATION.search(content):
            continue
        if API_UNVERIFIED_OK_ANNOTATION.search(content):
            continue
        if api_contract_exists(fpath):
            continue

        violations.append({
            "file": fpath,
            "urls": api_urls,
        })

    if not violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: Plan file contains unverified external API URLs",
        "=" * 70,
        "",
        "New plan files that reference external APIs must verify connectivity",
        "before being committed. Unverified API URLs in plans become",
        "unverified API assumptions in implementation.",
        "",
    ]

    for v in violations:
        lines.append(f"  {v['file']}")
        for lineno, url in v["urls"]:
            lines.append(f"    Line {lineno}: {url}")
        lines.append("")

    lines += [
        "To resolve, choose one of:",
        "",
        "  1. Verify the API is live and add to the plan file:",
        "       <!-- API-VERIFIED: confirmed reachable YYYY-MM-DD -->",
        "",
        "  2. Acknowledge unverified and document why it's OK:",
        "       <!-- API-URL-UNVERIFIED-OK: reason -->",
        "",
        "  3. Add a docs/api-contracts/<name>.json contract file",
        "     and stage it with this commit.",
        "",
        "See: helpers/check_api_connectivity.py for verification tooling.",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
