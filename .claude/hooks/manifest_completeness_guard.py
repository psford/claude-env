#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block commits that add or rename a hook /
helper file without a corresponding entry in tooling-manifest.json.

Background: tooling-manifest.json is the public contract that
claude-mac-env's setup.sh consumes to drive tiered feature selection.
On 2026-06-08, audit found .claude/hooks/ contained 54 Python scripts but
the manifest declared only 8 — 46 tools were invisible to bootstrap.
Patrick's intent for claude-env is that it BE the source of shared tooling
knowledge for new projects; that requires the manifest to be complete.

What this hook does:
- Fires on `git commit` Bash invocations from inside the claude-env repo.
- Identifies staged additions/renames under:
  - .claude/hooks/*.py
  - helpers/*.{py,sh,ps1}
  - helpers/hooks/*.py
- Cross-references each against tooling-manifest.json's `tools[].source`.
- Blocks (exit 2) if any new file is missing an entry.
- Escape hatch: a `<!-- MANIFEST-EXEMPT: reason -->` in the commit
  command, or `MANIFEST_EXEMPT=1` in the env.
"""

import json
import os
import re
import subprocess
import sys

MANIFEST_PATH = "tooling-manifest.json"
TRACKED_DIRS = (
    ".claude/hooks/",
    "helpers/",
    "helpers/hooks/",
)
TRACKED_EXTS = (".py", ".sh", ".ps1")


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _repo_root():
    rc, out = _run(["git", "rev-parse", "--show-toplevel"])
    return out.strip() if rc == 0 else None


def _is_claude_env_repo(root):
    if not root:
        return False
    return os.path.isfile(os.path.join(root, MANIFEST_PATH))


def _staged_additions(root):
    rc, out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=A"])
    if rc != 0:
        return []
    return [f for f in out.strip().splitlines()
            if any(f.startswith(d) for d in TRACKED_DIRS)
            and f.endswith(TRACKED_EXTS)]


def _manifest_sources(root):
    path = os.path.join(root, MANIFEST_PATH)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {t.get("source") for t in data.get("tools", []) if t.get("source")}


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    if os.environ.get("MANIFEST_EXEMPT") == "1":
        return 0
    if re.search(r'<!--\s*MANIFEST-EXEMPT\s*:', command, re.IGNORECASE):
        return 0

    root = _repo_root()
    if not _is_claude_env_repo(root):
        return 0

    additions = _staged_additions(root)
    if not additions:
        return 0

    sources = _manifest_sources(root)
    if sources is None:
        print(
            "\n[manifest_completeness_guard] WARNING: tooling-manifest.json "
            "unreadable; allowing commit.\n",
            file=sys.stderr
        )
        return 0

    missing = [p for p in additions if p not in sources]
    if not missing:
        return 0

    print(
        "\n[manifest_completeness_guard] BLOCKED\n"
        "These new hook/helper files are missing tooling-manifest.json entries:\n",
        file=sys.stderr
    )
    for p in missing:
        print(f"  {p}", file=sys.stderr)
    print(
        "\nFix: add an entry under `tools[]` for each file with name, source,\n"
        "     tier, language, feature, description. Then re-stage and commit.\n"
        "\n"
        "Exempt this commit (escape hatch) with:\n"
        "  MANIFEST_EXEMPT=1 git commit ...\n"
        "or include  <!-- MANIFEST-EXEMPT: reason -->  in the commit message.",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
