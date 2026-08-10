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

_sys_path_dir = os.path.dirname(os.path.abspath(__file__))
if _sys_path_dir not in sys.path:
    sys.path.insert(0, _sys_path_dir)
from _repo_context import target_data_file  # noqa: E402


# CH-58. This used to be dirname(__file__)/../artifact_paths.json, which names
# claude-env whichever repo is being written to -- and claude-env has no such
# file, so load_registry() returned {} and every write passed uninspected. The
# registry now comes from the repo that owns the file being written, and its
# absence means dormant, the same contract endpoint_registry_guard uses.
REGISTRY_RELATIVE = (".claude", "artifact_paths.json")

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


def load_registry(hook_input):
    """(artifacts_by_name, repo_root). Empty dict and None when there is none.

    The root is returned rather than discarded because canonical_path entries
    are repo-relative, and resolving them against the process cwd is the same
    wrong-repo bug one level down: the hook runs in the session's directory,
    which is usually not the repo being written to.
    """
    path = target_data_file(hook_input, *REGISTRY_RELATIVE)
    if not path:
        return {}, None
    root = os.path.dirname(os.path.dirname(path))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {a["name"]: a for a in data.get("artifacts", [])}, root
    except Exception:
        return {}, None


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

    registry, root = load_registry(hook_input)
    artifact = registry.get(artifact_name)
    if not artifact:
        return 0

    # Skip if canonical path doesn't exist in this repo (may be app-specific).
    # Resolved against the registry's own repo, not the process cwd.
    if not file_exists(os.path.join(root, artifact["canonical_path"])):
        return 0

    canonical = normalize_path(artifact["canonical_path"])
    actual = normalize_path(file_path)

    if actual == canonical or actual.startswith(canonical):
        return 0

    context = (
        f"ARTIFACT PATH GUARD — WRONG PATH DETECTED\n\n"
        f"You are writing to:   {file_path}\n"
        f"Canonical path is:    {artifact['canonical_path']}\n"
        # .get, not []. `consumer` is optional in a hand-written registry, and a
        # KeyError here is a PreToolUse hook exiting non-zero -- which BLOCKS the
        # write. An advisory hook that crashes is worse than one that is silent.
        # Never hit before CH-58 because no registry existed to be incomplete.
        f"Consumer that reads:  {artifact.get('consumer', '(not recorded)')}\n"
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
