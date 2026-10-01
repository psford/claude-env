#!/usr/bin/env bash
# bootstrap.sh — install/update the claude-env polytoken layer on this
# machine (Linux VM or MacBook). Idempotent: a second run with nothing
# changed makes no changes and creates no backups.
#
# Usage:
#   bash polytoken/bootstrap.sh              # install/update (prompts for
#                                            #   missing secrets)
#   bash polytoken/bootstrap.sh --check      # report drift, write nothing,
#                                            #   exit 0 only if fully clean
#   bash polytoken/bootstrap.sh --no-prompt  # install, never prompt; report
#                                            #   missing secrets instead
#   bash polytoken/bootstrap.sh --rollback   # restore the most recent
#                                            #   pre-install backups
#
# Env overrides (tests and non-standard clones):
#   POLYTOKEN_CONFIG_HOME  where config.yaml / hooks.json live
#                          (default: existing ~/.config/polytoken, else the
#                          OS default — ~/Library/Application
#                          Support/polytoken on macOS, ${XDG_CONFIG_HOME:-~
#                          /.config}/polytoken elsewhere)
#   CLONE_DIR              claude-env clone root (default: parent of this
#                          script's directory)
#   POLYTOKEN_BIN, GH_BIN  binaries (default: polytoken, gh)
#
# NOTE: this is NOT the repo's top-level bootstrap.sh (that one is
# WSL2/Claude-Code-specific). This script only touches:
#   <config-home>/config.yaml          (backed up, then installed)
#   <config-home>/hooks.json           (backed up if regular, then symlinked)
#   ~/.config/polytoken/secrets/       (created 0700; files 0600; git-ignored)
# It never reads or writes ~/.config/polytoken/permissions.local.yaml,
# prompt_history, or any session data.
#
# Portability: macOS bash 3.2 subset; no GNU-only tools.

set -u

CHECK=0
ROLLBACK=0
NO_PROMPT=0
for arg in "$@"; do
  case "$arg" in
    --check)    CHECK=1 ;;
    --rollback) ROLLBACK=1 ;;
    --no-prompt) NO_PROMPT=1 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${CLONE_DIR:-}" ]; then
  LAYER_DIR="${CLONE_DIR%/}/polytoken"
else
  LAYER_DIR="$SCRIPT_DIR"
fi
POLYTOKEN_BIN="${POLYTOKEN_BIN:-polytoken}"
GH_BIN="${GH_BIN:-gh}"
TODO_REPO="${TODO_REPO:-psford/claude-env}"

config_home_default() {
  if [ -n "${POLYTOKEN_CONFIG_HOME:-}" ]; then
    printf '%s\n' "$POLYTOKEN_CONFIG_HOME"
    return 0
  fi
  # Prefer wherever a config already lives…
  if [ -d "$HOME/.config/polytoken" ]; then
    printf '%s\n' "$HOME/.config/polytoken"
    return 0
  fi
  case "$(uname -s)" in
    Darwin) printf '%s\n' "$HOME/Library/Application Support/polytoken" ;;
    *) printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/polytoken" ;;
  esac
}
CONFIG_HOME="$(config_home_default)"
# Secrets are ALWAYS at this fixed path on every OS — config.template.yaml
# references it literally so the template stays byte-identical per machine.
SECRETS_DIR="$HOME/.config/polytoken/secrets"
TEMPLATE="$LAYER_DIR/config.template.yaml"
LAYER_HOOKS="$LAYER_DIR/hooks.json"
INSTALLED_HOOKS="$CONFIG_HOME/hooks.json"
INSTALLED_CONFIG="$CONFIG_HOME/config.yaml"
STAMP_FILE="$CONFIG_HOME/.polytoken-layer-stamp"
VERSION_FILE="$LAYER_DIR/VERSION"

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

ts() { date +%Y%m%d%H%M%S; }

newest_backup() { # newest_backup <name> — echoes newest <name>.bak.<ts>
  # Timestamp suffixes are %Y%m%d%H%M%S, so reverse lexicographic sort is
  # chronological (find, not ls, per shellcheck SC2012).
  find "$CONFIG_HOME" -maxdepth 1 -name "$1.bak.*" 2>/dev/null | sort -r | head -1
}
backup_count() { # backup_count <name>
  find "$CONFIG_HOME" -maxdepth 1 -name "$1.bak.*" 2>/dev/null | wc -l | tr -d ' '
}

# ------------------------------------------------------------------ checks

CHECK_FINDINGS=""
finding() { CHECK_FINDINGS="${CHECK_FINDINGS}${1}
"; }

poly_version_report() { # -> "ok" | "mismatch:<actual>" | "missing"
  command -v "$POLYTOKEN_BIN" >/dev/null 2>&1 || { printf 'missing'; return 0; }
  local actual expected
  expected="$(cat "$VERSION_FILE" 2>/dev/null)"
  actual="$("$POLYTOKEN_BIN" --version 2>/dev/null | awk '{print $2}')"
  if [ -z "$actual" ]; then printf 'missing'; return 0; fi
  if [ -n "$expected" ] && [ "$actual" != "$expected" ]; then
    printf 'mismatch:%s' "$actual"
  else
    printf 'ok'
  fi
}

gh_report() { # -> "ok:<account>" | "missing" | "unauthenticated"
  command -v "$GH_BIN" >/dev/null 2>&1 || { printf 'missing'; return 0; }
  if ! "$GH_BIN" auth status >/dev/null 2>&1; then printf 'unauthenticated'; return 0; fi
  local acct
  acct="$("$GH_BIN" auth status 2>&1 | sed -n 's/.*account \([A-Za-z0-9_-]*\).*/\1/p' | head -1)"
  printf 'ok:%s' "${acct:-unknown}"
}

labels_present() { # labels_present <label> -> yes/no/unknown
  command -v "$GH_BIN" >/dev/null 2>&1 || { printf 'unknown'; return 0; }
  "$GH_BIN" auth status >/dev/null 2>&1 || { printf 'unknown'; return 0; }
  if "$GH_BIN" label list --repo "$TODO_REPO" --limit 100 \
      --json name --jq '.[].name' 2>/dev/null | grep -qx "$1"; then
    printf 'yes'
  else
    printf 'no'
  fi
}

secrets_missing() { # echoes names of absent secrets
  local f name
  for f in "$LAYER_DIR"/secrets.example/*.example; do
    [ -f "$f" ] || continue
    name="$(basename "$f" .example)"
    if [ ! -f "$SECRETS_DIR/$name" ]; then
      printf '%s\n' "$name"
    fi
  done
  return 0
}

config_state() { # -> missing | clean | drifted
  [ -f "$INSTALLED_CONFIG" ] || { printf 'missing'; return 0; }
  if cmp -s "$TEMPLATE" "$INSTALLED_CONFIG" 2>/dev/null; then
    printf 'clean'
  else
    printf 'drifted'
  fi
}

hooks_state() { # -> missing | clean | drifted:<reason>
  local target
  if [ ! -e "$INSTALLED_HOOKS" ] && [ ! -L "$INSTALLED_HOOKS" ]; then
    printf 'missing'; return 0
  fi
  if [ -L "$INSTALLED_HOOKS" ]; then
    target="$(readlink "$INSTALLED_HOOKS")"
    case "$target" in
      "$LAYER_HOOKS") printf 'clean' ;;
      *) printf 'drifted:symlink points to %s' "$target" ;;
    esac
    return 0
  fi
  printf 'drifted:regular file, not the layer symlink'
}

# --------------------------------------------------------------- rollback

do_rollback() {
  local b acted=0
  [ -d "$CONFIG_HOME" ] || die "nothing to roll back: no $CONFIG_HOME"
    for name in config.yaml hooks.json; do
    b="$(newest_backup "$name")"
    if [ -n "$b" ]; then
      # rm first: cp through a symlink would write into the link target.
      rm -f "$CONFIG_HOME/$name"
      cp "$b" "$CONFIG_HOME/$name"
      say "rolled back $name from $(basename "$b")"
      acted=1
    fi
  done
  if [ -f "$STAMP_FILE" ]; then
    while IFS= read -r fresh; do
      [ -n "$fresh" ] || continue
      if [ -f "$CONFIG_HOME/$fresh" ]; then
        rm -f "$CONFIG_HOME/$fresh"
        say "removed $fresh (fresh install, no pre-install state to restore)"
        acted=1
      fi
    done < "$STAMP_FILE"
    rm -f "$STAMP_FILE"
  fi
  [ "$acted" = 1 ] || say "nothing to roll back (no backups, no fresh-install stamp)"
  exit 0
}
[ "$ROLLBACK" = 1 ] && do_rollback

# ------------------------------------------------------------------ check

run_checks() {
  local v g
  v="$(poly_version_report)"
  case "$v" in
    ok) ;;
    missing) finding "polytoken: not found on PATH" ;;
    *) warn "version mismatch: layer tested against $(cat "$VERSION_FILE" 2>/dev/null || echo '?'), this machine runs ${v#mismatch:}"; finding "polytoken: version mismatch (layer $(cat "$VERSION_FILE" 2>/dev/null || echo '?') vs installed ${v#mismatch:})" ;;
  esac
  g="$(gh_report)"
  case "$g" in
    ok:*) ;;
    missing) finding "gh: not found on PATH (todo bridge will not work)" ;;
    unauthenticated) finding "gh: auth check failed — not authenticated, or GitHub unreachable (todo bridge will not work)" ;;
  esac
  command -v jq >/dev/null 2>&1 || finding "jq: not found on PATH (hooks require it)"
  # The layer's installed paths (hooks.json handler strings, discovery dirs)
  # all reference ~/projects/claude-env — a clone anywhere else silently
  # dead-ends them. Hermetic runs (POLYTOKEN_CONFIG_HOME override, i.e.
  # tests) are exempt.
  if [ -z "${POLYTOKEN_CONFIG_HOME:-}" ] && \
     [ "$LAYER_DIR" != "$HOME/projects/claude-env/polytoken" ]; then
    finding "clone: layer lives at $LAYER_DIR but hooks/discovery reference ~/projects/claude-env — clone there (or symlink it)"
  fi
  case "$(config_state)" in
    clean) ;;
    missing) finding "config: missing ($INSTALLED_CONFIG)" ;;
    drifted) finding "config: drifted from template" ;;
  esac
  hs="$(hooks_state)"
  case "$hs" in
    clean) ;;
    missing) finding "hooks: missing ($INSTALLED_HOOKS)" ;;
    drifted:*) finding "hooks: ${hs#drifted:}" ;;
  esac
  local miss
  miss="$(secrets_missing)"
  [ -z "$miss" ] || finding "secrets: missing $(printf '%s' "$miss" | paste -sd, -)"
  for lbl in todo in-progress; do
    case "$(labels_present "$lbl")" in
      yes) ;;
      no) finding "labels: '$lbl' missing on $TODO_REPO" ;;
      unknown) finding "labels: unknown (gh unavailable — cannot verify '$lbl')" ;;
    esac
  done
}

[ "$CHECK" = 0 ] || {
  run_checks
  if [ -n "$CHECK_FINDINGS" ]; then
    say "polytoken layer check — DRIFT:"
    printf '%s' "$CHECK_FINDINGS"
    exit 1
  fi
  say "polytoken layer check — clean"
  exit 0
}

# ----------------------------------------------------------------- install

[ -f "$TEMPLATE" ]  || die "layer incomplete: no $TEMPLATE (wrong CLONE_DIR?)"
[ -f "$LAYER_HOOKS" ] || die "layer incomplete: no $LAYER_HOOKS"
command -v "$POLYTOKEN_BIN" >/dev/null 2>&1 || die "$POLYTOKEN_BIN not found on PATH"

v="$(poly_version_report)"
case "$v" in
  ok) say "polytoken: $( "$POLYTOKEN_BIN" --version 2>/dev/null ) (matches layer VERSION)" ;;
  missing) die "polytoken not found on PATH" ;;
  *) warn "polytoken version mismatch: layer tested against $(cat "$VERSION_FILE"), this machine runs ${v#mismatch:} — behavior may differ" ;;
esac

g="$(gh_report)"
case "$g" in
  ok:*) say "gh: authenticated as ${g#ok:}" ;;
  *) warn "gh not usable (${g}) — config/hooks still install, but the todo bridge will not sync until gh works" ;;
esac
command -v jq >/dev/null 2>&1 || warn "jq not found on PATH — the todo hooks require jq (brew install jq / apt install jq)"

mkdir -p "$CONFIG_HOME" || die "cannot create $CONFIG_HOME"

FRESH=""
# config.yaml — backup only when it will actually change (idempotency).
case "$(config_state)" in
  clean)
    say "config: already current ($INSTALLED_CONFIG)"
    ;;
  missing)
    cp "$TEMPLATE" "$INSTALLED_CONFIG"
    FRESH="${FRESH}config.yaml
"
    say "config: installed -> $INSTALLED_CONFIG"
    ;;
  drifted)
    b="$INSTALLED_CONFIG.bak.$(ts)"
    cp "$INSTALLED_CONFIG" "$b"
    chmod 600 "$b" 2>/dev/null || true  # may contain pre-layer plaintext keys
    cp "$TEMPLATE" "$INSTALLED_CONFIG"
    say "config: updated -> $INSTALLED_CONFIG (backup: $(basename "$b"))"
    ;;
esac

# hooks.json — symlink into the clone so hook updates arrive with git pulls.
case "$(hooks_state)" in
  clean)
    say "hooks: already symlinked -> $LAYER_HOOKS"
    ;;
  missing)
    ln -s "$LAYER_HOOKS" "$INSTALLED_HOOKS"
    FRESH="${FRESH}hooks.json
"
    say "hooks: symlinked -> $INSTALLED_HOOKS"
    ;;
  drifted:*)
    if [ ! -L "$INSTALLED_HOOKS" ]; then
      b="$INSTALLED_HOOKS.bak.$(ts)"
      cp "$INSTALLED_HOOKS" "$b"
      chmod 600 "$b" 2>/dev/null || true
      say "hooks: backed up existing file to $(basename "$b")"
    fi
    rm -f "$INSTALLED_HOOKS"
    ln -s "$LAYER_HOOKS" "$INSTALLED_HOOKS"
    say "hooks: symlinked -> $INSTALLED_HOOKS"
    ;;
esac

if [ -n "$FRESH" ]; then
  printf '%s' "$FRESH" > "$STAMP_FILE"
fi

# secrets — fixed dir, 0700/0600; prompt for absent ones unless --no-prompt.
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR" 2>/dev/null || true
for f in "$LAYER_DIR"/secrets.example/*.example; do
  [ -f "$f" ] || continue
  name="$(basename "$f" .example)"
  if [ -f "$SECRETS_DIR/$name" ]; then
    chmod 600 "$SECRETS_DIR/$name" 2>/dev/null || true
    say "secrets: $name present"
    continue
  fi
  if [ "$NO_PROMPT" = 1 ]; then
    warn "secrets: $name MISSING (--no-prompt; add it at $SECRETS_DIR/$name)"
    continue
  fi
  printf 'value for secret "%s" (input hidden, empty to skip): ' "$name"
  val=""
  read -rs val || val=""
  printf '\n'
  if [ -n "$val" ]; then
    printf '%s' "$val" > "$SECRETS_DIR/$name"
    chmod 600 "$SECRETS_DIR/$name"
    say "secrets: $name written"
  else
    warn "secrets: $name skipped — add it at $SECRETS_DIR/$name and re-run"
  fi
done

# tracker labels — idempotent create.
if command -v "$GH_BIN" >/dev/null 2>&1 && "$GH_BIN" auth status >/dev/null 2>&1; then
  for lbl in todo in-progress; do
    case "$(labels_present "$lbl")" in
      yes) say "labels: '$lbl' present" ;;
      *)
        if "$GH_BIN" label create "$lbl" --repo "$TODO_REPO" \
            --color "$( [ "$lbl" = todo ] && printf 5319E7 || printf FBCA04 )" \
            --description "polytoken todo tracker" >/dev/null 2>&1; then
          say "labels: '$lbl' created"
        else
          warn "could not create label '$lbl' on $TODO_REPO"
        fi
        ;;
    esac
  done
fi

# readiness summary
say ""
say "---- polytoken layer summary ----"
say "clone:      $LAYER_DIR"
say "config:     $INSTALLED_CONFIG ($(config_state))"
say "hooks:      $INSTALLED_HOOKS ($(hooks_state))"
say "secrets:    $SECRETS_DIR ($( printf '%s' "$(secrets_missing)" | grep -c . || true ) missing)"
say "backups:    config=$(backup_count config.yaml) hooks=$(backup_count hooks.json)"
if command -v "$POLYTOKEN_BIN" >/dev/null 2>&1; then
  dout="$("$POLYTOKEN_BIN" doctor 2>&1)"
  say "discovery:  $(printf '%s\n' "$dout" | grep -F 'skill(s) discovered' | head -1)"
  say "            $(printf '%s\n' "$dout" | grep -F 'subagent(s) discovered' | head -1)"
fi
say "next:       reload config (restart session) and run tests/run.sh or acceptance.sh"
exit 0
