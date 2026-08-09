#!/usr/bin/env bash
# Point a repository's core.hooksPath at the shared, versioned git hooks.
#
# The hooks live in claude-env and are read from there, so a fix reaches every
# repo without copying -- the copying is what produced five instances of one
# guard's fix never reaching its sibling.
#
# Usage:
#   helpers/install-git-hooks.sh                 # report every workspace repo
#   helpers/install-git-hooks.sh --install PATH  # install into one repo
#   helpers/install-git-hooks.sh --install-all   # install into every workspace repo
#   helpers/install-git-hooks.sh --uninstall PATH
#
# Reporting is the default because a script that changes 11 repositories the
# moment it is run is not a script anybody runs twice.
set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/shared/git-hooks"
WORKSPACE="${CLAUDE_WORKSPACE_ROOT:-$HOME/projects}"

if [ ! -x "$HOOKS_DIR/pre-commit" ] || [ ! -x "$HOOKS_DIR/pre-push" ]; then
  echo "error: hooks not found or not executable in $HOOKS_DIR" >&2
  echo "       run: chmod +x $HOOKS_DIR/*" >&2
  exit 1
fi

repos() {
  find "$WORKSPACE" -maxdepth 2 -type d -name .git -printf '%h\n' 2>/dev/null | sort
}

state_of() {
  local repo="$1" current
  current=$(git -C "$repo" config --local --get core.hooksPath 2>/dev/null || true)
  if [ -z "$current" ]; then
    echo "unset"
  elif [ "$current" = "$HOOKS_DIR" ]; then
    echo "installed"
  else
    echo "other:$current"
  fi
}

install_into() {
  local repo="$1" before
  before=$(state_of "$repo")
  case "$before" in
    installed)
      printf '  %-40s already installed\n' "$(basename "$repo")"
      return 0 ;;
    other:*)
      # Never silently replace someone else's hooks path. Overwriting a repo's
      # existing hooks is exactly the kind of surprise that gets tooling banned.
      printf '  %-40s SKIPPED — core.hooksPath is %s\n' "$(basename "$repo")" "${before#other:}"
      return 0 ;;
  esac
  git -C "$repo" config --local core.hooksPath "$HOOKS_DIR"
  printf '  %-40s installed\n' "$(basename "$repo")"
}

uninstall_from() {
  git -C "$1" config --local --unset core.hooksPath 2>/dev/null || true
  printf '  %-40s removed\n' "$(basename "$1")"
}

case "${1:---report}" in
  --report)
    echo "shared hooks: $HOOKS_DIR"
    echo "workspace:    $WORKSPACE"
    echo
    while read -r repo; do
      [ -n "$repo" ] || continue
      printf '  %-40s %s\n' "$(basename "$repo")" "$(state_of "$repo")"
    done < <(repos)
    echo
    echo "install with: $0 --install-all"
    ;;
  --install)
    [ $# -ge 2 ] || { echo "usage: $0 --install <repo>" >&2; exit 2; }
    install_into "$(cd "$2" && pwd)"
    ;;
  --install-all)
    while read -r repo; do
      [ -n "$repo" ] || continue
      install_into "$repo"
    done < <(repos)
    ;;
  --uninstall)
    [ $# -ge 2 ] || { echo "usage: $0 --uninstall <repo>" >&2; exit 2; }
    uninstall_from "$(cd "$2" && pwd)"
    ;;
  *)
    echo "unknown option: $1" >&2
    exit 2 ;;
esac
