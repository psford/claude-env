#!/usr/bin/env bash
# todo-restore.sh — session_start hook injecting the shared todo tracker
# into every new session's context.
#
# stdin : polytoken event JSON
#         {"event":"session_start","session_id":"<id>",...}
# stdout: {"outcome":"allow","additional_context":"Tracked todos …"}
#
# session_start BLOCKS: polytoken waits for this handler (30s deadline).
# This script therefore always answers fast, never stalls, and fails open —
# worst case with GitHub hung is ~TODO_RESTORE_TIMEOUT seconds, then a bare
# allow and the session starts anyway.
#
# Side effects, in order:
#   1. Record the current session id where todo-sync.sh can find it (it
#      gates todo_delete closes on it). This happens before any network I/O
#      so it survives GitHub being down.
#   2. Fetch open `todo`-labeled issues under a portable internal timeout
#      (background fetch + watchdog kill — macOS has no GNU timeout).
#   3. On success refresh the last-good cache; on timeout/error/offline
#      serve the cache marked stale, or a bare allow if there is no cache.
#
# Portability: bash 3.2 subset (no mapfile, no associative arrays, no
# flock), GNU/BSD-neutral tools only.

set -u

# Hook handlers inherit the daemon's environment (verified on 0.8.17),
# which can lack Homebrew on macOS — see the matching comment in
# todo-sync.sh. jq must be visible before anything else runs here.
for _d in /opt/homebrew/bin /usr/local/bin; do
  if [ -d "$_d" ]; then
    case ":$PATH:" in
      *":$_d:"*) ;;
      *) PATH="$_d:$PATH" ;;
    esac
  fi
done

GH_BIN="${GH_BIN:-gh}"
TODO_REPO="${TODO_REPO:-psford/claude-env}"
STATE_DIR="${POLYTOKEN_STATE_HOME:-$HOME/.local/share/polytoken}"
CACHE="$STATE_DIR/todo-restore.cache"
SESSION_FILE="$STATE_DIR/todo-session.current"
TITLES_DIR="$STATE_DIR/todo-titles"
LABEL_WIP="in-progress"
LIST_LIMIT=30
TIMEOUT_SECS="${TODO_RESTORE_TIMEOUT:-5}"

allow_bare() {
  printf '{"outcome":"allow"}\n'
  exit 0
}

EVENT="$(cat 2>/dev/null || true)"
command -v jq >/dev/null 2>&1 || allow_bare

# Housekeeping (cheap, before any network I/O): sweep abandoned fetch
# temp files from SIGKILLed runs (>1 day old) and prune title-map dirs of
# sessions long gone (>14 days; the current session's dir is fresh).
find "$STATE_DIR" -maxdepth 1 -name 'todo-restore.list.*' -mtime +1 \
  -exec rm -f {} + 2>/dev/null
[ -d "$TITLES_DIR" ] && find "$TITLES_DIR" -mindepth 1 -maxdepth 1 -type d \
  -mtime +14 -exec rm -rf {} + 2>/dev/null

# 1. Current session id — from the event payload (hook env vars are not set
#    on 0.8.17; the payload is the source that works). The daemon pid is
#    recorded alongside it so todo-sync.sh can detect that the pointer
#    belongs to a different live session on this machine (session todo ids
#    restart at 1 per session, so cross-session trust resolves wrong
#    titles). 0 = "could not determine" — todo-sync then trusts the pointer.
daemon_pid() {
  local p="$PPID" comm i=0
  while [ "$i" -lt 10 ] && [ "${p:-0}" -gt 1 ] 2>/dev/null; do
    comm="$(ps -p "$p" -o comm= 2>/dev/null || true)"
    case "$comm" in
      *polytoken*) printf '%s' "$p"; return 0 ;;
    esac
    p="$(ps -p "$p" -o ppid= 2>/dev/null | tr -d ' ')"
    [ -n "$p" ] || break
    i=$((i + 1))
  done
  printf '0'
}

SID="$(printf '%s' "$EVENT" | jq -r '.session_id // empty' 2>/dev/null)"
if [ -n "$SID" ]; then
  DPID="${POLYTOKEN_DAEMON_PID:-}"
  if [ -z "$DPID" ]; then
    DPID="$(daemon_pid)"
  fi
  mkdir -p "$STATE_DIR" "$TITLES_DIR/$SID" 2>/dev/null || true
  tmp="${SESSION_FILE}.tmp.$$"
  if printf '%s %s' "$SID" "$DPID" > "$tmp" 2>/dev/null; then
    mv -f "$tmp" "$SESSION_FILE" 2>/dev/null || rm -f "$tmp" 2>/dev/null
  fi
fi

# 2. Fetch under an internal timeout.
LIST_FILE="${STATE_DIR}/todo-restore.list.$$"
: > "$LIST_FILE" 2>/dev/null
if command -v "$GH_BIN" >/dev/null 2>&1; then
  "$GH_BIN" issue list --repo "$TODO_REPO" --label todo --state open \
    --json number,title,labels --limit "$((LIST_LIMIT + 1))" \
    > "$LIST_FILE" 2>/dev/null &
  gh_pid=$!
  # The watchdog MUST NOT inherit this script's stdout: session_start is a
  # blocking event and the daemon reads handler stdout until EOF — an
  # orphaned sleep holding the pipe would add TIMEOUT_SECS to every
  # session start even after this script exits.
  ( sleep "$TIMEOUT_SECS" && kill "$gh_pid" 2>/dev/null ) >/dev/null 2>&1 &
  watchdog=$!
  wait "$gh_pid" 2>/dev/null
  kill "$watchdog" 2>/dev/null
  wait "$watchdog" 2>/dev/null
fi

list_is_valid() { # list_is_valid <file>
  [ -s "$1" ] && jq -e 'type == "array"' "$1" >/dev/null 2>&1
}

# 3. Build the injected context from the freshest source available.
build_context() { # build_context <json-file> <stale-note>
  local f total lines base
  f="$1"
  total="$(jq -r 'length' "$f" 2>/dev/null)"
  if [ "${total:-0}" -eq 0 ]; then
    printf '%s' "Tracked todo store (${TODO_REPO} issues): empty — no open tracked todos."
    return 0
  fi
  # String literals must live OUTSIDE \(...) interpolations — jq 1.6
  # rejects escaped quotes inside interpolation.
  lines="$(jq -r --arg wip "$LABEL_WIP" "sort_by(.number) | .[0:${LIST_LIMIT}][] |
    (any(.labels[]?; (.name? // .) == \$wip)) as \$iswip |
    \"#\\(.number)\" + (if \$iswip then \" [in-progress]\" else \"\" end) + \" \\(.title)\"" "$f" 2>/dev/null \
    | paste -sd ';' -)"
  base="Tracked todos (GitHub Issues in ${TODO_REPO}, the cross-machine todo store): ${lines}"
  if [ "$total" -gt "$LIST_LIMIT" ]; then
    base="$base (+$((total - LIST_LIMIT)) more open todos not shown — finish work to shrink the backlog)"
  fi
  base="$base. Adopt these as session todos (todo_create) if you will work them this session; todo_create dedupes against this list; todo_complete closes the tracked issue; todo_delete of an adopted item only tidies the session and does not close the issue."
  if [ -n "${2:-}" ]; then
    base="$base ${2}"
  fi
  printf '%s' "$base"
}

if list_is_valid "$LIST_FILE"; then
  cp "$LIST_FILE" "$CACHE" 2>/dev/null || true
  ctx="$(build_context "$LIST_FILE" "")"
elif list_is_valid "$CACHE"; then
  ctx="$(build_context "$CACHE" \
    "(cached list — GitHub unreachable, possibly stale.)")"
else
  rm -f "$LIST_FILE" 2>/dev/null
  allow_bare
fi
rm -f "$LIST_FILE" 2>/dev/null

# Emit the decision as a single JSON object; jq -Rn does the escaping.
printf '{"outcome":"allow","additional_context":%s}\n' \
  "$(jq -Rn --arg v "$ctx" '$v' 2>/dev/null)"
exit 0
