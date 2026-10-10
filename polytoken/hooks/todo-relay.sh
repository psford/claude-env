#!/usr/bin/env bash
# todo-relay.sh — pre_model_turn hook that surfaces todo-sync outcomes in the
# session that caused them.
#
# todo-sync.sh runs on post_tool_use, which is fire-and-forget: Polytoken
# discards anything it returns, so the session never learns whether its
# todo_create filed an issue, deduped against a tracked one, or failed
# silently (2026-10-10: a Mac session read that silence as "todo_create does
# not consult GitHub at all" — it does, invisibly). This relay closes the
# loop: todo-sync's log() also appends session-tagged notice lines to
# todo-notices.pending, and this hook drains the current session's lines
# into the next model turn as additional_context (a system-reminder).
#
# stdin : polytoken event JSON {"event":"pre_model_turn",...}
# stdout: {"outcome":"proceed","additional_context":"..."} when notices are
#         pending for this session; nothing (exit 0) otherwise — the common
#         path is one stat and must stay free of gh/jq when nothing pends.
#
# Session resolution prefers the event payload's session_id, then the
# POLYTOKEN_SESSION_ID env (unset on 0.8.17-era daemons), then the
# todo-session.current pointer todo-restore.sh writes at session_start.
# A stale pointer can mis-attribute a drain to the wrong live session —
# worst case duplicated feedback, never lost tracker state.
#
# Lines tagged session:? (origin written with no resolvable session — e.g.
# jq/gh missing before any pointer existed) are machine-level distress and
# drain into whichever session turns next.
#
# Portability: bash 3.2 subset, no network, no gh call, ever.

set -u

# See todo-sync.sh: daemon handlers can lack Homebrew on macOS.
for _d in /opt/homebrew/bin /usr/local/bin; do
  if [ -d "$_d" ]; then
    case ":$PATH:" in
      *":$_d:"*) ;;
      *) PATH="$_d:$PATH" ;;
    esac
  fi
done

STATE_DIR="${POLYTOKEN_STATE_HOME:-$HOME/.local/share/polytoken}"
NOTICE_FILE="$STATE_DIR/todo-notices.pending"

# Fast path: nothing pending for anyone.
[ -s "$NOTICE_FILE" ] || exit 0

command -v jq >/dev/null 2>&1 || exit 0

EVENT="$(cat 2>/dev/null || true)"

SID="$(printf '%s' "$EVENT" | jq -r '.session_id // empty' 2>/dev/null)"
[ -n "$SID" ] || SID="${POLYTOKEN_SESSION_ID:-}"
if [ -z "$SID" ]; then
  line="$(cat "$STATE_DIR/todo-session.current" 2>/dev/null || true)"
  SID="${line%% *}"
fi
[ -n "$SID" ] || exit 0

# Drain: this session's lines plus session:? distress lines; everything
# else stays for its owning session. The read-then-rewrite window can drop
# a concurrently appended line — feedback is best-effort, tracker state
# never lives here.
mine="$(awk -F'\t' -v s="session:$SID" \
  '$1 == s || $1 == "session:?"' "$NOTICE_FILE" 2>/dev/null || true)"
[ -n "$mine" ] || exit 0

rest="$(awk -F'\t' -v s="session:$SID" \
  '$1 != s && $1 != "session:?"' "$NOTICE_FILE" 2>/dev/null || true)"
tmp="${NOTICE_FILE}.tmp.$$"
if [ -n "$rest" ]; then
  printf '%s\n' "$rest" > "$tmp" 2>/dev/null \
    && mv -f "$tmp" "$NOTICE_FILE" 2>/dev/null
  rm -f "$tmp" 2>/dev/null
else
  rm -f "$NOTICE_FILE" 2>/dev/null
fi

# "session:<id>\ttodo_create: message" -> "todo_create: message"
body="$(printf '%s\n' "$mine" | cut -f2- | paste -sd ' ' -)"
ctx="Todo tracker sync: ${body}"
printf '{"outcome":"proceed","additional_context":%s}\n' \
  "$(printf '%s' "$ctx" | jq -R . 2>/dev/null)"
exit 0
