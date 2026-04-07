#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Retrospective area overlap guard.

Fires on Write tool. When a NEW source file (does not exist on disk) is being
written to an area that has open retrospective mitigations, outputs an advisory
context block reminding Claude to apply the relevant mitigations.

Area tags are read from docs/retrospectives/*-mitigations.md files.
Area → path mappings:
  js-map, js-layer, js-cache, js-coord, js-xss  → wwwroot/js/*.js
  external-api                                    → *Importer*.cs
  dotnet-test                                     → *Tests/*.cs

Advisory only — always exits 0. Injects additionalContext JSON to stdout.
"""

import json
import os
import re
import sys
import glob


# Mapping from area tag to file path patterns (regex)
AREA_PATH_PATTERNS = {
    "js-map":     re.compile(r'wwwroot[/\\]js[/\\][^/\\]+\.js$', re.IGNORECASE),
    "js-layer":   re.compile(r'wwwroot[/\\]js[/\\][^/\\]+\.js$', re.IGNORECASE),
    "js-cache":   re.compile(r'wwwroot[/\\]js[/\\][^/\\]+\.js$', re.IGNORECASE),
    "js-coord":   re.compile(r'wwwroot[/\\]js[/\\][^/\\]+\.js$', re.IGNORECASE),
    "js-xss":     re.compile(r'wwwroot[/\\]js[/\\][^/\\]+\.js$', re.IGNORECASE),
    "external-api": re.compile(r'Importer[^/\\]*\.cs$', re.IGNORECASE),
    "dotnet-test":  re.compile(r'Tests[/\\][^/\\]+\.cs$', re.IGNORECASE),
}

AREA_TAG_PATTERN = re.compile(
    r'<!--\s*area-tags\s*:\s*([^>]+)-->', re.IGNORECASE
)

# Matches "- [ ] #N ..." lines (open mitigations)
OPEN_MITIGATION_PATTERN = re.compile(r'^\s*-\s*\[\s*\]\s*#(\d+)\s+(.+)$')


def find_repo_root():
    """Walk up from this hook's location to find the repo root."""
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    # .claude/hooks/ → .claude/ → repo root
    return os.path.abspath(os.path.join(hook_dir, "..", ".."))


def read_mitigation_files(repo_root):
    """
    Returns a list of dicts:
      { "file": path, "area_tags": [str], "open_mitigations": [(num, desc)] }
    for each *-mitigations.md that has open items.
    """
    retro_dir = os.path.join(repo_root, "docs", "retrospectives")
    if not os.path.isdir(retro_dir):
        return []

    results = []
    pattern = os.path.join(retro_dir, "*-mitigations.md")
    for fpath in glob.glob(pattern):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        # Extract area tags
        tag_match = AREA_TAG_PATTERN.search(content)
        if not tag_match:
            continue
        tags_raw = tag_match.group(1)
        area_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        # Extract open mitigations
        open_mitigations = []
        for line in content.splitlines():
            m = OPEN_MITIGATION_PATTERN.match(line)
            if m:
                open_mitigations.append((m.group(1), m.group(2).strip()))

        if area_tags and open_mitigations:
            results.append({
                "file": os.path.basename(fpath),
                "area_tags": area_tags,
                "open_mitigations": open_mitigations,
            })

    return results


def find_matching_areas(file_path, mitigation_files):
    """
    For a given file_path being written, return list of mitigation entries
    whose area tags map to a pattern that matches file_path.
    """
    normalized = file_path.replace("\\", "/")
    matches = []
    for entry in mitigation_files:
        for tag in entry["area_tags"]:
            pattern = AREA_PATH_PATTERNS.get(tag)
            if pattern and pattern.search(normalized):
                matches.append(entry)
                break  # Only add entry once even if multiple tags match
    return matches


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Write":
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Only fire for NEW files (do not exist on disk)
    if os.path.exists(file_path):
        sys.exit(0)

    repo_root = find_repo_root()
    mitigation_files = read_mitigation_files(repo_root)
    if not mitigation_files:
        sys.exit(0)

    matching = find_matching_areas(file_path, mitigation_files)
    if not matching:
        sys.exit(0)

    # Build advisory context
    lines = [
        f"ADVISORY: New file '{os.path.basename(file_path)}' overlaps with areas",
        "that have open retrospective mitigations.",
        "",
        "Before finalizing this file, review and apply the relevant mitigations:",
        "",
    ]

    for entry in matching:
        lines.append(f"  Source: {entry['file']}")
        lines.append(f"  Area tags: {', '.join(entry['area_tags'])}")
        lines.append(f"  Open mitigations ({len(entry['open_mitigations'])}):")
        for num, desc in entry["open_mitigations"]:
            lines.append(f"    #{num} {desc}")
        lines.append("")

    lines += [
        "These mitigations exist because past sessions had problems in this area.",
        "Apply any relevant ones now rather than discovering the same issues again.",
        f"Full details: docs/retrospectives/ in the claude-env repo.",
    ]

    context = "\n".join(lines)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
