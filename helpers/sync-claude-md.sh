#!/usr/bin/env bash
# sync-claude-md.sh — assemble a companion repo's CLAUDE.md from shared
# claude-env fragments + the repo's own CLAUDE.local.md.
#
# This is the distribution mechanism for the shared-knowledge layer: the
# behavioral rules (Principles, Git Flow, coding standards, etc.) live once
# in claude-env/shared/claude-md/ and are concatenated into each repo's
# CLAUDE.md, so they stop drifting across repos. Project-specific content
# stays hand-edited in CLAUDE.local.md.
#
# Per-repo config at <repo>/.claude/claude-md.json:
#   {
#     "fragments": ["00-universal", "git-flow-develop-main", "stack-web-azure"],
#     "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" }
#   }
# Fragments resolve to $CLAUDE_ENV_ROOT/shared/claude-md/<name>.md.
# {{VAR}} tokens in fragments are replaced from "vars".
#
# Usage:
#   sync-claude-md.sh <repo-dir>            # (re)generate <repo-dir>/CLAUDE.md
#   sync-claude-md.sh --check <repo-dir>    # exit 3 if CLAUDE.md is out of sync
#
# Exit codes: 0 ok / in-sync; 2 usage or IO error; 3 drift (--check only).
set -uo pipefail

CHECK=0
REPO=""
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    -*) echo "sync-claude-md.sh: unknown flag $arg" >&2; exit 2 ;;
    *) REPO="$arg" ;;
  esac
done

if [ -z "$REPO" ]; then
  echo "usage: sync-claude-md.sh [--check] <repo-dir>" >&2
  exit 2
fi

# Locate claude-env root: explicit env var, else derive from this script's
# location (<root>/helpers/sync-claude-md.sh).
if [ -n "${CLAUDE_ENV_ROOT:-}" ]; then
  ENV_ROOT="$CLAUDE_ENV_ROOT"
else
  ENV_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi

FRAG_DIR="$ENV_ROOT/shared/claude-md"

CHECK="$CHECK" REPO="$REPO" FRAG_DIR="$FRAG_DIR" python3 - <<'PY'
import json
import os
import sys

check = os.environ["CHECK"] == "1"
repo = os.environ["REPO"]
frag_dir = os.environ["FRAG_DIR"]

cfg_path = os.path.join(repo, ".claude", "claude-md.json")
try:
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
except FileNotFoundError:
    sys.stderr.write(f"sync-claude-md: no config at {cfg_path}\n")
    sys.exit(2)
except (json.JSONDecodeError, ValueError) as e:
    sys.stderr.write(f"sync-claude-md: bad JSON in {cfg_path}: {e}\n")
    sys.exit(2)

fragments = cfg.get("fragments", [])
variables = cfg.get("vars", {}) or {}

header = (
    "<!-- GENERATED FILE — DO NOT EDIT. -->\n"
    "<!-- Shared rules: claude-env/shared/claude-md/. Project rules: CLAUDE.local.md. -->\n"
    "<!-- Regenerate: helpers/sync-claude-md.sh <repo> -->\n"
)

parts = [header]

for name in fragments:
    fpath = os.path.join(frag_dir, f"{name}.md")
    try:
        with open(fpath, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"sync-claude-md: fragment not found: {name} ({fpath})\n")
        sys.exit(2)
    for key, val in variables.items():
        text = text.replace("{{" + key + "}}", str(val))
    parts.append(text.rstrip("\n"))

local_path = os.path.join(repo, "CLAUDE.local.md")
if os.path.isfile(local_path):
    with open(local_path, encoding="utf-8") as f:
        parts.append(f.read().rstrip("\n"))

output = "\n\n".join(parts) + "\n"

out_path = os.path.join(repo, "CLAUDE.md")

if check:
    try:
        with open(out_path, encoding="utf-8") as f:
            current = f.read()
    except FileNotFoundError:
        current = None
    if current == output:
        sys.exit(0)
    sys.stderr.write(
        f"sync-claude-md: {out_path} is OUT OF SYNC with shared fragments. "
        f"Run: helpers/sync-claude-md.sh {repo}\n"
    )
    sys.exit(3)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(output)
print(f"sync-claude-md: wrote {out_path} ({len(fragments)} fragment(s) + local)")
sys.exit(0)
PY