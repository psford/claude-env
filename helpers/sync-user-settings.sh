#!/usr/bin/env bash
# sync-user-settings.sh — mirror ~/.claude/settings.json into claude-env.
#
# The global Claude Code settings file is where every hook wiring, permission
# rule, and plugin enablement actually lives, but it sits outside version
# control. That is how five psford-hook-* plugin directories sat unregistered
# and silently non-functional (2026-08-07): nothing could diff intent against
# reality. This mirrors the file into the repo so its history is reviewable
# and a drift check can run in pre-commit or CI.
#
# The mirror is descriptive, not authoritative — ~/.claude/settings.json is
# what Claude Code reads. Use --restore only to recover a lost or broken file.
#
# The mirror contains absolute /home/patrick paths and is therefore personal,
# not portable. It is tiered "personal" in tooling-manifest.json so external
# bootstrap tooling does not pick it up.
#
# Usage:
#   sync-user-settings.sh              # capture ~/.claude/settings.json -> repo
#   sync-user-settings.sh --check      # exit 3 if the mirror has drifted
#   sync-user-settings.sh --restore    # write repo mirror -> ~/.claude/settings.json
#
# Exit codes: 0 ok / in-sync; 2 usage or IO error; 3 drift (--check only).
set -uo pipefail

MODE="capture"
for arg in "$@"; do
  case "$arg" in
    --check)   MODE="check" ;;
    --restore) MODE="restore" ;;
    *) echo "sync-user-settings.sh: unknown argument $arg" >&2; exit 2 ;;
  esac
done

# Locate claude-env root: explicit env var, else derive from this script's
# location (<root>/helpers/sync-user-settings.sh).
if [ -n "${CLAUDE_ENV_ROOT:-}" ]; then
  ENV_ROOT="$CLAUDE_ENV_ROOT"
else
  ENV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

LIVE="${CLAUDE_USER_SETTINGS:-$HOME/.claude/settings.json}"
MIRROR="$ENV_ROOT/infrastructure/claude-settings/user-settings.json"

# Normalise before comparing so key order and indentation never register as
# drift — only real content changes should fail --check.
normalise() {
  python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as fh:
        json.dump(json.load(fh), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
except FileNotFoundError:
    sys.exit(4)
except json.JSONDecodeError as exc:
    print(f"sync-user-settings.sh: {sys.argv[1]} is not valid JSON: {exc}", file=sys.stderr)
    sys.exit(2)
' "$1"
}

case "$MODE" in
  capture)
    if [ ! -f "$LIVE" ]; then
      echo "sync-user-settings.sh: no settings file at $LIVE" >&2
      exit 2
    fi
    mkdir -p "$(dirname "$MIRROR")" || exit 2
    normalise "$LIVE" > "$MIRROR.tmp" || { rm -f "$MIRROR.tmp"; exit 2; }
    mv "$MIRROR.tmp" "$MIRROR" || exit 2
    echo "captured $LIVE -> $MIRROR"
    ;;

  check)
    if [ ! -f "$MIRROR" ]; then
      echo "DRIFT: no mirror at $MIRROR — run sync-user-settings.sh" >&2
      exit 3
    fi
    if [ ! -f "$LIVE" ]; then
      echo "DRIFT: no live settings at $LIVE" >&2
      exit 3
    fi
    live_norm="$(normalise "$LIVE")"   || exit 2
    mirror_norm="$(normalise "$MIRROR")" || exit 2
    if [ "$live_norm" = "$mirror_norm" ]; then
      echo "in sync: $MIRROR"
      exit 0
    fi
    echo "DRIFT between $LIVE and $MIRROR:" >&2
    diff <(printf '%s\n' "$mirror_norm") <(printf '%s\n' "$live_norm") >&2
    echo "run sync-user-settings.sh to capture, or --restore to revert" >&2
    exit 3
    ;;

  restore)
    if [ ! -f "$MIRROR" ]; then
      echo "sync-user-settings.sh: no mirror at $MIRROR" >&2
      exit 2
    fi
    if [ -f "$LIVE" ]; then
      cp "$LIVE" "$LIVE.bak-restore" || exit 2
      echo "backed up existing settings to $LIVE.bak-restore"
    fi
    mkdir -p "$(dirname "$LIVE")" || exit 2
    normalise "$MIRROR" > "$LIVE.tmp" || { rm -f "$LIVE.tmp"; exit 2; }
    mv "$LIVE.tmp" "$LIVE" || exit 2
    echo "restored $MIRROR -> $LIVE"
    ;;
esac
