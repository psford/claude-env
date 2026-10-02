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
grep -qF "$LINE_PATH" "$ZSHRC" || printf '%s\n' "$LINE_PATH" >> "$ZSHRC"
# NOTE: POLYTOKEN_CONFIG_PATH is deliberately NOT set anymore. Pointing it
# at the template file made polytoken derive paths like
# <template>/prompt_history — "Not a directory" — and killed prompt
# history. The config is installed as a real file below instead; any
# stale POLYTOKEN_CONFIG_PATH line is removed by the cleaning step.
[ -f "$HOME/.zshrcsource" ] && rm -f "$HOME/.zshrcsource"
say "zshrc: PATH export ensured; POLYTOKEN_CONFIG_PATH lines removed"
say "-- zshrc tail --"
run tail -8 "$ZSHRC"

# ------------------------------------------------------- hooks + config
# ~/.config/polytoken is the config location polytoken searches on macOS
# too (the ~/Library/Application Support path is NOT searched — proven on
# this bring-up: a config there is dead while doctor reports 'no config
# file found in any searched location'). hooks.json has no env override,
# so the symlink goes into every candidate config dir.
CFG_DIR="$HOME/.config/polytoken"
mkdir -p "$CFG_DIR"
if [ -f "$CFG_DIR/config.yaml" ] && ! cmp -s "$CFG_TEMPLATE" "$CFG_DIR/config.yaml"; then
  cp "$CFG_DIR/config.yaml" "$CFG_DIR/config.yaml.bak.$TS"
  say "config: updated in $CFG_DIR (backup kept)"
fi
cmp -s "$CFG_TEMPLATE" "$CFG_DIR/config.yaml" 2>/dev/null \
  || cp "$CFG_TEMPLATE" "$CFG_DIR/config.yaml"
for d in "$CFG_DIR" "$HOME/Library/Application Support/polytoken"; do
  mkdir -p "$d" 2>/dev/null || true
  ln -sfh "$HOOKS_SRC" "$d/hooks.json" 2>/dev/null \
    || ln -sf "$HOOKS_SRC" "$d/hooks.json"
done
say "config: $CFG_DIR/config.yaml installed; hooks.json symlinked"

say "-- config dirs --"
run ls -la "$HOME/.config/polytoken" \
     "$HOME/Library/Application Support/polytoken"
say "-- secrets sizes (bytes; values never logged) --"
run wc -c "$HOME/.config/polytoken/secrets/"* 2>/dev/null

# ------------------------------------------------------------- verify
# Unset defensively: a stale exported override would mask the real test
# of whether the installed config is discovered on its own.
unset POLYTOKEN_CONFIG_PATH || true
say "-- polytoken --"
run sh -c 'command -v polytoken && polytoken --version'
say "-- doctor (no env overrides) --"
if command -v polytoken >/dev/null 2>&1; then
  if polytoken doctor 2>&1 | grep -E '✓|✗' | tee -a "$LOG"; then :; fi
  FAILS="$(polytoken doctor 2>&1 | grep -c '✗' || true)"
else
  say "polytoken not on PATH in this shell"
  FAILS=1
fi

# --------------------------------------------------- live restore probe
# Two questions: (1) does the hook work from this user context at all —
# tested with a SCRATCH state dir so the real session pointer is not
# touched; (2) did the user's live TUI session actually fire session_start
# — proven by the real state dir containing todo-session.current with a
# recent mtime and todo-restore.cache.
say "-- live restore probe (scratch state) --"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/pt-probe.XXXXXX")"
PROBE_OUT="$(printf '{"event":"session_start","session_id":"mac-setup-probe"}' \
  | POLYTOKEN_STATE_HOME="$SCRATCH" bash \
    "$HOME/projects/claude-env/polytoken/hooks/todo-restore.sh" 2>/dev/null || true)"
say "$PROBE_OUT"
rm -rf "$SCRATCH"
say "-- real state dir (did the live session fire the hook?) --"
run sh -c 'ls -la "$HOME/.local/share/polytoken/" 2>/dev/null | grep -E "todo-|total" || echo "(no todo-* state files yet)"'
run sh -c 'cat "$HOME/.local/share/polytoken/todo-session.current" 2>/dev/null || echo "(no session pointer)"'
say "-- open tracked todos --"
run gh issue list --repo "$TODO_REPO" --label todo --state open \
     --json number,title --limit 5

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
