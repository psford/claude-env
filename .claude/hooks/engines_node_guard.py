#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block `npm install` in Node projects that
have no version pinning.

Background: Node version drift between local dev and CI has bitten
multiple companion projects. stock-analyzer pins NODE_VERSION='20.x' in
GH Actions but has no .nvmrc and no engines.node in package.json. road-trip
similarly. photo-portfolio also lacks both. The result is "works on my
machine" lockfile regenerations, peer-dep skew, and silent install
failures when CI runner Node major version drifts.

What this hook does:
- Fires on Bash `npm install` / `npm i` / `npm ci` / `pnpm install` /
  `yarn install` commands.
- Walks up from the current directory to find the nearest package.json.
- Blocks (exit 2) if BOTH of the following are true:
   - package.json has no `"engines": {"node": "..."}` entry
   - the package.json's directory (or any parent up to a .git root) has
     no `.nvmrc` or `.node-version` file
- Escape hatch: set `ENGINES_NODE_OK=1` in the env (e.g. when installing
  in a tooling repo that genuinely doesn't need a pin), or pass
  `--ignore-engines` to the command.
"""

import json
import os
import re
import sys

NPM_INSTALL_RE = re.compile(
    r'\b(?:npm\s+(?:install|i|ci)|pnpm\s+install|yarn\s+install)\b'
)


def _find_package_json(start_dir):
    """Walk up from start_dir looking for package.json. Stop at filesystem root or a .git dir."""
    cur = os.path.abspath(start_dir)
    while True:
        pkg = os.path.join(cur, "package.json")
        if os.path.isfile(pkg):
            return cur, pkg
        parent = os.path.dirname(cur)
        if parent == cur:
            return None, None
        if os.path.isdir(os.path.join(cur, ".git")) and not os.path.isfile(pkg):
            return None, None
        cur = parent


def _has_engines_node(pkg_path):
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    engines = data.get("engines") or {}
    return bool(engines.get("node"))


def _has_nvmrc(pkg_dir):
    cur = pkg_dir
    while True:
        for fname in (".nvmrc", ".node-version"):
            if os.path.isfile(os.path.join(cur, fname)):
                return True
        parent = os.path.dirname(cur)
        if parent == cur:
            return False
        if os.path.isdir(os.path.join(cur, ".git")):
            return False
        cur = parent


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    if hook_input.get("tool_name") != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if not NPM_INSTALL_RE.search(command):
        return 0

    if os.environ.get("ENGINES_NODE_OK") == "1":
        return 0
    if "--ignore-engines" in command:
        return 0

    cwd = hook_input.get("cwd") or os.getcwd()
    pkg_dir, pkg_path = _find_package_json(cwd)
    if not pkg_path:
        return 0

    has_engines = _has_engines_node(pkg_path)
    has_nvmrc = _has_nvmrc(pkg_dir)

    if has_engines or has_nvmrc:
        return 0

    print(
        f"\n[engines_node_guard] BLOCKED\n"
        f"package.json: {pkg_path}\n"
        f"This project has no Node version pin. Pick one:\n"
        f"  1. Add an .nvmrc with the major version (e.g. `echo 20 > .nvmrc`)\n"
        f"  2. Add an engines.node entry to package.json:\n"
        f"     \"engines\": {{ \"node\": \"20.x\" }}\n"
        f"  3. Bypass: ENGINES_NODE_OK=1 npm install\n"
        f"  4. Bypass per-command: pass --ignore-engines\n",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
