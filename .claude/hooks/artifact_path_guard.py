#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Artifact path registry guard.

Fires on Write/Edit. Checks the target path against the canonical artifact
registry (.claude/artifact_paths.json). If the filename matches a known
artifact but the full path differs from canonical, injects a correction.

Advisory only — does not block.
"""

import json
import sys
import os


REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifact_paths.json"
)

FILENAME_TO_ARTIFACT = {
    "sessionstate.md": "sessionState",
    "claudelog.md": "claudeLog",
    "whileyouwereaway.md": "whileYouWereAway",
    "technical_spec.md": "technicalSpec",
    "functional_spec.md": "functionalSpec",
    "roadmap.md": "roadmap",
    "installed_plugins.json": "pluginInstalledList",
    "marketplace.json": "pluginMarketplace",
    "retrospective-log.md": "retrospectiveLog",
}


def normalize_path(path):
    return path.replace("\\", "/").lower().rstrip("/")


def load_registry():
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {a["name"]: a for a in data.get("artifacts", [])}
    except Exception:
        return {}


def file_exists(path):
    """Check if a file exists at the given path."""
    return os.path.exists(path) and os.path.isfile(path)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        return 0

    filename = os.path.basename(file_path).lower()
    artifact_name = FILENAME_TO_ARTIFACT.get(filename)
    if not artifact_name:
        return 0

    registry = load_registry()
    artifact = registry.get(artifact_name)
    if not artifact:
        return 0

    # Skip if canonical path doesn't exist in this repo (may be app-specific)
    if not file_exists(artifact["canonical_path"]):
        return 0

    canonical = normalize_path(artifact["canonical_path"])
    actual = normalize_path(file_path)

    if actual == canonical or actual.startswith(canonical):
        return 0

    context = (
        f"ARTIFACT PATH GUARD — WRONG PATH DETECTED\n\n"
        f"You are writing to:   {file_path}\n"
        f"Canonical path is:    {artifact['canonical_path']}\n"
        f"Consumer that reads:  {artifact['consumer']}\n"
        f"Notes:                {artifact.get('notes', '')}\n\n"
        f"If you write to the wrong path, the consumer CANNOT find this artifact.\n"
        f"REQUIRED: Change the target path to the canonical path shown above."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
