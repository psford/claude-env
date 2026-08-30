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
import re
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

# CE-5.1. A fragment with no {{substitutions}} is IDENTICAL in every repo, so it
# is LINKED into .claude/rules/ instead of copied into CLAUDE.md. Its content
# then exists in exactly one file and cannot fall out of line — there is nothing
# to drift, rather than drift being caught quickly.
#
# A fragment that DOES carry substitutions cannot be linked: a symlink cannot
# turn {{WORKING_BRANCH}} into "develop", and a linked one would put the literal
# token into context. Those stay generated.
VAR_TOKEN = re.compile(r"\{\{[A-Z_]+\}\}")

rules_dir = os.path.join(repo, ".claude", "rules")
parts = [header]
linked, generated = [], []

for name in fragments:
    fpath = os.path.join(frag_dir, f"{name}.md")
    try:
        with open(fpath, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"sync-claude-md: fragment not found: {name} ({fpath})\n")
        sys.exit(2)
    if VAR_TOKEN.search(text):
        for key, val in variables.items():
            text = text.replace("{{" + key + "}}", str(val))
        left = VAR_TOKEN.findall(text)
        if left:
            sys.stderr.write(
                f"sync-claude-md: {name} still holds {sorted(set(left))} after "
                f"substitution — add them to \"vars\" in {cfg_path}\n")
            sys.exit(2)
        parts.append(text.rstrip("\n"))
        generated.append(name)
    else:
        linked.append((name, fpath))

# Relative, so the link survives the whole tree being cloned somewhere else.
# Absolute would be simpler and would break the moment the tree moved.
for name, fpath in linked:
    os.makedirs(rules_dir, exist_ok=True)
    dest = os.path.join(rules_dir, f"{name}.md")
    target = os.path.relpath(fpath, rules_dir)
    if os.path.islink(dest) and os.readlink(dest) == target:
        continue
    if check:
        continue  # the check below reports it; do not mutate during --check
    if os.path.lexists(dest):
        os.unlink(dest)
    os.symlink(target, dest)

local_path = os.path.join(repo, "CLAUDE.local.md")
if os.path.isfile(local_path):
    with open(local_path, encoding="utf-8") as f:
        parts.append(f.read().rstrip("\n"))

output = "\n\n".join(parts) + "\n"

out_path = os.path.join(repo, "CLAUDE.md")

if check:
    # Absence replaces drift as the way inheritance fails, so the link is
    # checked FIRST and loudly: a repo with no link inherits nothing while
    # looking exactly like a healthy one.
    problems = []
    for name, fpath in linked:
        dest = os.path.join(rules_dir, f"{name}.md")
        if not os.path.islink(dest):
            problems.append(f"{dest} is not a symlink — this repo inherits nothing from {name}")
        elif not os.path.exists(dest):
            problems.append(f"{dest} is a BROKEN link to {os.readlink(dest)}")
        elif os.path.realpath(dest) != os.path.realpath(fpath):
            problems.append(f"{dest} points at {os.path.realpath(dest)}, not {fpath}")
    if problems:
        for p in problems:
            sys.stderr.write(f"sync-claude-md: {p}\n")
        sys.stderr.write(f"sync-claude-md: run helpers/sync-claude-md.sh {repo}\n")
        sys.exit(3)
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
print(f"sync-claude-md: wrote {out_path} ({len(generated)} generated + local); "
      f"linked {len(linked)}: {', '.join(n for n, _ in linked) or 'none'}")
sys.exit(0)
PY