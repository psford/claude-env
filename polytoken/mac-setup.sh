#!/usr/bin/env bash
# mac-setup.sh — one-command Mac bring-up repair + verification, and the
# closing of the relay loop: this script POSTS its report to the tracker
# issue so the VM side can continue without copy-paste between machines.
# (Commands travel to the Mac by `git pull`; results travel back by
# GitHub. No email.)
#
# Idempotent — safe to re-run. Your ~/.zshrc is backed up before any edit.
# Env: TODO_REPO, MAC_SETUP_REPORT_ISSUE (default 155), MAC_SETUP_NO_POST=1
# to skip the GitHub report.

set -u

TODO_REPO="${TODO_REPO:-psford/claude-env}"
REPORT_ISSUE="${MAC_SETUP_REPORT_ISSUE:-155}"
ZSHRC="$HOME/.zshrc"
TS="$(date +%Y%m%d%H%M%S)"
HOOKS_SRC="$HOME/projects/claude-env/polytoken/hooks.json"
CFG_TEMPLATE="$HOME/projects/claude-env/polytoken/config.template.yaml"
LOG="$(mktemp "${TMPDIR:-/tmp}/pt-mac-setup.XXXXXX")"

say() { printf '%s\n' "$*" | tee -a "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; }

say "== polytoken mac-setup — $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(hostname) =="

# ---------------------------------------------------------------- zshrc
# Backup, then remove only lines this layer's earlier bring-up could have
# damaged (any POLYTOKEN_CONFIG_PATH line, and known newline-mangle
# signatures), then ensure the two clean exports exist.
if [ -f "$ZSHRC" ]; then
  cp "$ZSHRC" "$ZSHRC.bak.$TS"
  TMP="$(mktemp)"
  grep -v 'POLYTOKEN_CONFIG_PATH' "$ZSHRC" 2>/dev/null \
    | grep -v 'zshrcsource' | grep -v 'zshrcmkdir' | grep -v 'config.template.yaml..source' \
    | grep -v 'PATH=.*source ' > "$TMP" || true
  mv "$TMP" "$ZSHRC"
  say "zshrc: cleaned damaged lines (backup: ~/.zshrc.bak.$TS)"
else
  touch "$ZSHRC"
fi

# Single quotes are deliberate: the .zshrc line must contain a literal
# $HOME so the shell expands it at login, not at write time.
# shellcheck disable=SC2016
LINE_PATH='export PATH="$HOME/.local/bin:$PATH"'
# shellcheck disable=SC2016
LINE_CFG='export POLYTOKEN_CONFIG_PATH="$HOME/projects/claude-env/polytoken/config.template.yaml"'
grep -qF "$LINE_PATH" "$ZSHRC" || printf '%s\n' "$LINE_PATH" >> "$ZSHRC"
grep -qF "$LINE_CFG" "$ZSHRC" || printf '%s\n' "$LINE_CFG" >> "$ZSHRC"
[ -f "$HOME/.zshrcsource" ] && rm -f "$HOME/.zshrcsource"
say "zshrc: PATH and POLYTOKEN_CONFIG_PATH exports ensured"
say "-- zshrc tail --"
run tail -8 "$ZSHRC"

# ------------------------------------------------------- hooks + config
# config comes from the git template via POLYTOKEN_CONFIG_PATH (verified
# to load on 0.8.17, substitutions included); hooks.json has no env
# override, so the symlink goes into every candidate config dir.
export POLYTOKEN_CONFIG_PATH="$CFG_TEMPLATE"
for d in "$HOME/.config/polytoken" "$HOME/Library/Application Support/polytoken"; do
  mkdir -p "$d" 2>/dev/null || true
  ln -sfh "$HOOKS_SRC" "$d/hooks.json" 2>/dev/null \
    || ln -sf "$HOOKS_SRC" "$d/hooks.json"
done
say "hooks.json: symlinked into both candidate config dirs"

say "-- config dirs --"
run ls -la "$HOME/.config/polytoken" \
     "$HOME/Library/Application Support/polytoken"
say "-- secrets sizes (bytes; values never logged) --"
run wc -c "$HOME/.config/polytoken/secrets/"* 2>/dev/null

# ------------------------------------------------------------- verify
say "-- polytoken --"
run sh -c 'command -v polytoken && polytoken --version'
say "-- doctor --"
if command -v polytoken >/dev/null 2>&1; then
  if polytoken doctor 2>&1 | grep -E '✓|✗' | tee -a "$LOG"; then :; fi
  FAILS="$(polytoken doctor 2>&1 | grep -c '✗' || true)"
else
  say "polytoken not on PATH in this shell"
  FAILS=1
fi

# -------------------------------------------------------------- report
if [ "${MAC_SETUP_NO_POST:-0}" != 1 ]; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh issue comment "$REPORT_ISSUE" --repo "$TODO_REPO" \
        --body-file "$LOG" >/dev/null 2>&1; then
      say "report: posted to $TODO_REPO#$REPORT_ISSUE"
    else
      say "report: FAILED to post to $TODO_REPO#$REPORT_ISSUE (see $LOG)"
    fi
  else
    say "report: gh unavailable — not posted (log kept at $LOG)"
  fi
fi

say ""
if [ "${FAILS:-0}" = "0" ]; then
  say "RESULT: doctor is green."
  say "Next: run  exec zsh  (or open a new terminal) so your interactive"
  say "shell picks up the env, then:  bash ~/projects/claude-env/polytoken/tests/acceptance.sh"
else
  say "RESULT: doctor still failing — the report above (also posted to #$REPORT_ISSUE)"
  say "has everything the VM side needs to diagnose. Nothing else to relay by hand."
fi
rm -f "$LOG"
exit 0
