#!/usr/bin/env bash
# todo-sync.sh — post_tool_use hook (matcher: todo_*) that mirrors session
# todos into GitHub Issues, making psford/claude-env the cross-machine todo
# store shared by the Linux VM and the MacBook.
#
# stdin : polytoken event JSON
#         {"event":"post_tool_use","tool_name":"todo_create",
#          "input":{"title":"...","description":"..."}}
#         (todo_update/complete/delete carry "input":{"id",...}; the todo
#         record is already mutated — and on delete already gone — when this
#         fires, so titles come from a machine-local map and the session
#         todo store.)
# env   : GH_BIN (default gh), TODO_REPO (default psford/claude-env),
#         POLYTOKEN_STATE_HOME (default ~/.local/share/polytoken),
#         POLYTOKEN_SESSION_ID (0.8.17 does not set it; kept for the day it
#         does — see docs/decisions.md, polytoken layer entry).
# out   : nothing. post_tool_use is fire-and-forget; every path exits 0 and
#         failures append one line to todo-sync.log.
#
# Label semantics (additive, never swapped): an issue carries `todo` for its
# whole life; `in-progress` is added/removed to mirror session status. A
# swap-based scheme would strand issues with no label on partial failure and
# break the restore query.
#
# Delete semantics: closing on delete is gated by the issue body's
# session:/machine: markers. Only the session that created the issue (same
# session id AND same machine) closes it on todo_delete; anything else is an
# adopted tracker item being tidied and stays open.
#
# Portability: macOS ships bash 3.2 — no associative arrays, no mapfile, no
# GNU timeout, no flock(1). The lock below is a mkdir lockdir with a
# find -mmin staleness check instead.

set -u

GH_BIN="${GH_BIN:-gh}"
TODO_REPO="${TODO_REPO:-psford/claude-env}"
STATE_DIR="${POLYTOKEN_STATE_HOME:-$HOME/.local/share/polytoken}"
SESSIONS_DIR="$STATE_DIR/sessions-v1"
LOG_FILE="$STATE_DIR/todo-sync.log"
LOCK_DIR="$STATE_DIR/todo-sync.lockdir"
TITLES_DIR="$STATE_DIR/todo-titles"
LABEL_TODO="todo"
LABEL_WIP="in-progress"

log() { # log <tool> <message> — one line per failure or skip, never fails
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" \
    >> "$LOG_FILE" 2>/dev/null || true
}

EVENT="$(cat 2>/dev/null || true)"
TOOL="$(printf '%s' "$EVENT" | jq -r '.tool_name // empty' 2>/dev/null)"

# todo_list fires constantly (every sidebar refresh) and must be free:
# no gh call, no log line, exit before any setup.
[ "$TOOL" = "todo_list" ] && exit 0
case "$TOOL" in
  todo_create|todo_update|todo_complete|todo_delete) ;;
  *) exit 0 ;;
esac

command -v jq >/dev/null 2>&1 || { log "$TOOL" "jq not found — cannot sync"; exit 0; }
command -v "$GH_BIN" >/dev/null 2>&1 || { log "$TOOL" "$GH_BIN not found — cannot sync"; exit 0; }

# ---------------------------------------------------------------- locking
# mkdir is atomic, so it doubles as the lock test. Stale after >1 minute
# (find -mmin works on BSD and GNU). A holder that crashed between mkdir
# and stamping leaves no stamp file — treat that as stale, not busy. Every
# exit path of this script removes the lockdir (trap below), including the
# failure paths: the lock must never outlive the process that owns it.
acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then :; else
    if [ ! -f "$LOCK_DIR/stamp" ] || \
       [ -n "$(find "$LOCK_DIR/stamp" -mmin +1 -print 2>/dev/null)" ]; then
      rm -rf "$LOCK_DIR" 2>/dev/null
      mkdir "$LOCK_DIR" 2>/dev/null || return 1
    else
      # A sibling hook is mid-sync (batched todo_create can race the
      # dedupe). Wait up to ~10s for it to finish rather than skip.
      i=0
      while [ "$i" -lt 20 ] && [ -d "$LOCK_DIR" ]; do
        sleep 0.5
        i=$((i + 1))
      done
      [ -d "$LOCK_DIR" ] && return 1
      mkdir "$LOCK_DIR" 2>/dev/null || return 1
    fi
  fi
  echo $$ > "$LOCK_DIR/pid" 2>/dev/null
  : > "$LOCK_DIR/stamp" 2>/dev/null
  return 0
}

OWN_LOCK=0
if acquire_lock; then
  OWN_LOCK=1
else
  log "$TOOL" "sync lock busy after 10s — skipping this event"
  exit 0
fi
# Invoked only via the EXIT/INT/TERM traps below, hence the shellcheck
# "unreachable" note.
# shellcheck disable=SC2317
cleanup() {
  if [ "$OWN_LOCK" = 1 ]; then
    rm -rf "$LOCK_DIR" 2>/dev/null || true
  fi
  return 0
}
trap cleanup EXIT
trap 'cleanup; exit 0' INT TERM

# ------------------------------------------------------- session identity
# Fallback ladder (0.8.17 sets no POLYTOKEN_* env in hook handlers):
# env var if present, else the current-session file written by
# todo-restore.sh at session_start (its event payload carries session_id),
# else empty — and an empty session id must never close an issue.
SID="${POLYTOKEN_SESSION_ID:-}"
if [ -z "$SID" ]; then
  SID="$(cat "$STATE_DIR/todo-session.current" 2>/dev/null || true)"
fi
MACHINE="$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo unknown)"
TODAY="$(date -u +%Y-%m-%d)"

# ------------------------------------------------------------ title maps
# post_tool_use fires after the mutation; on delete the record is already
# gone, so the pre-delete title must come from the map we keep current on
# every non-delete event (snapshot from the session todo store).
map_file() { printf '%s/%s/%s' "$TITLES_DIR" "$1" "$2"; }

map_get() { # map_get <session> <todo-id> -> title or empty
  [ -n "$1" ] && [ -n "$2" ] || return 0
  cat "$(map_file "$1" "$2")" 2>/dev/null || true
}

snapshot_titles() { # copy id->title pairs from the session todo store
  [ -n "$SID" ] || return 0
  local d f id t
  d="$SESSIONS_DIR/$SID/todos"
  [ -d "$d" ] || return 0
  mkdir -p "$TITLES_DIR/$SID" 2>/dev/null || true
  for f in "$d"/*.json; do
    [ -f "$f" ] || continue
    id="$(jq -r '.id // empty' "$f" 2>/dev/null)"
    t="$(jq -r '.title // empty' "$f" 2>/dev/null)"
    if [ -n "$id" ] && [ -n "$t" ]; then
      printf '%s' "$t" > "$(map_file "$SID" "$id")" 2>/dev/null || true
    fi
  done
  return 0
}

store_title() { # store_title <todo-id> -> title or empty
  [ -n "$SID" ] || return 0
  [ -n "$1" ] || return 0
  jq -r '.title // empty' "$SESSIONS_DIR/$SID/todos/$1.json" 2>/dev/null || true
}

# ------------------------------------------------------------- gh queries
# One issue-list fetch per event, cached until a mutation invalidates it.
CACHED_LIST=""
issues_json() {
  if [ -z "$CACHED_LIST" ]; then
    CACHED_LIST="$("$GH_BIN" issue list --repo "$TODO_REPO" \
      --label "$LABEL_TODO" --state open \
      --json number,title,body,labels --limit 100 2>/dev/null)" || CACHED_LIST=""
  fi
  printf '%s' "$CACHED_LIST"
}

nums_for_title() { # nums_for_title <title> -> matching open issue numbers
  printf '%s' "$(issues_json)" \
    | jq -r --arg t "$1" '.[] | select(.title == $t) | .number' 2>/dev/null
}

pick_issue() { # pick_issue <title> [prefer_session] -> one number or empty
  local nums count pref
  nums="$(nums_for_title "$1")"
  [ -n "$nums" ] || return 0
  count="$(printf '%s\n' "$nums" | wc -l | tr -d ' ')"
  if [ "$count" -gt 1 ] && [ -n "${2:-}" ]; then
    pref="$(printf '%s' "$(issues_json)" | jq -r --arg t "$1" --arg s "$2" \
      '.[] | select(.title == $t and ((.body // "") | contains("session:" + $s))) |
       .number' 2>/dev/null | head -1)"
    [ -n "$pref" ] && { printf '%s\n' "$pref"; return 0; }
  fi
  printf '%s\n' "$nums" | head -1
}

body_for_num() { # body_for_num <number> -> issue body or empty
  printf '%s' "$(issues_json)" \
    | jq -r --argjson n "$1" '.[] | select(.number == $n) | .body // ""' 2>/dev/null
}

close_issue() { # close_issue <number> <title> <comment>
  if "$GH_BIN" issue close "$1" --repo "$TODO_REPO" --comment "$3" \
      >/dev/null 2>&1; then
    CACHED_LIST=""
  else
    log "$TOOL" "gh issue close #$1 failed for '$2'"
  fi
  return 0
}

# ----------------------------------------------------------- tool branches

do_create() {
  local title desc dup body url
  title="$(printf '%s' "$EVENT" | jq -r '.input.title // empty' 2>/dev/null)"
  desc="$(printf '%s' "$EVENT" | jq -r '.input.description // empty' 2>/dev/null)"
  if [ -z "$title" ]; then
    log todo_create "event input has no title — skipping"
    return 0
  fi
  dup="$(nums_for_title "$title" | head -1)"
  if [ -n "$dup" ]; then
    log todo_create "dedupe: issue #$dup already tracks '$title'"
    snapshot_titles
    return 0
  fi
  body="$(printf '%s\n\n%s\n%s\n%s' "$desc" "session:${SID}" "machine:${MACHINE}" "date:${TODAY}")"
  url="$("$GH_BIN" issue create --repo "$TODO_REPO" --label "$LABEL_TODO" \
    --title "$title" --body "$body" 2>/dev/null)" || {
    log todo_create "gh issue create failed for '$title'"
    snapshot_titles
    return 0
  }
  CACHED_LIST=""
  log todo_create "created issue ${url##*/} for '$title'"
  snapshot_titles
  return 0
}

complete_title() { # complete_title <title>
  local num
  num="$(pick_issue "$1" "$SID")"
  if [ -z "$num" ]; then
    log "$TOOL" "no open $LABEL_TODO issue for '$1'"
    return 0
  fi
  # Completion is a real outcome for adopted todos too — no session gate.
  close_issue "$num" "$1" \
    "Completed in session ${SID:-unknown} on ${MACHINE} (${TODAY})."
  return 0
}

do_complete() {
  local id title
  id="$(printf '%s' "$EVENT" | jq -r '.input.id // empty' 2>/dev/null)"
  title="$(map_get "$SID" "$id")"
  [ -z "$title" ] && title="$(store_title "$id")"
  if [ -z "$title" ]; then
    log todo_complete "no title mapping for todo id ${id:-?} — cannot close issue"
    return 0
  fi
  complete_title "$title"
  snapshot_titles
  return 0
}

do_update() {
  local id new_title status old_title num
  id="$(printf '%s' "$EVENT" | jq -r '.input.id // empty' 2>/dev/null)"
  new_title="$(printf '%s' "$EVENT" | jq -r '.input.title // empty' 2>/dev/null)"
  status="$(printf '%s' "$EVENT" | jq -r '.input.status // empty' 2>/dev/null)"
  old_title="$(map_get "$SID" "$id")"
  [ -z "$old_title" ] && old_title="$(store_title "$id")"

  # Rename: the issue still carries the pre-update title.
  if [ -n "$new_title" ] && [ -n "$old_title" ] && [ "$new_title" != "$old_title" ]; then
    num="$(pick_issue "$old_title" "$SID")"
    if [ -n "$num" ]; then
      if "$GH_BIN" issue edit "$num" --repo "$TODO_REPO" --title "$new_title" \
          >/dev/null 2>&1; then
        CACHED_LIST=""
        log todo_update "renamed issue #$num '$old_title' -> '$new_title'"
      else
        log todo_update "gh issue edit #$num title failed ('$old_title' -> '$new_title')"
      fi
    else
      log todo_update "rename: no open issue for '$old_title'"
    fi
  fi

  case "$status" in
    in_progress)
      num="$(pick_issue "${new_title:-$old_title}" "$SID")"
      if [ -n "$num" ]; then
        if "$GH_BIN" issue edit "$num" --repo "$TODO_REPO" --add-label "$LABEL_WIP" \
            >/dev/null 2>&1; then
          CACHED_LIST=""
        else
          log todo_update "add-label $LABEL_WIP failed on issue #$num"
        fi
      fi
      ;;
    pending)
      num="$(pick_issue "${new_title:-$old_title}" "$SID")"
      if [ -n "$num" ]; then
        if "$GH_BIN" issue edit "$num" --repo "$TODO_REPO" --remove-label "$LABEL_WIP" \
            >/dev/null 2>&1; then
          CACHED_LIST=""
        else
          log todo_update "remove-label $LABEL_WIP failed on issue #$num"
        fi
      fi
      ;;
    done)
      complete_title "${new_title:-$old_title}"
      ;;
  esac
  snapshot_titles
  return 0
}

do_delete() {
  local id title nums
  id="$(printf '%s' "$EVENT" | jq -r '.input.id // empty' 2>/dev/null)"
  if [ -z "$SID" ]; then
    # Never-close fallback: without a session id we cannot prove this
    # session created the issue, and an unprovable delete must not close.
    # Checked BEFORE the title-map lookup: with no session id the map is
    # unusable anyway (it is keyed by session).
    log todo_delete "session id unknown — never-close fallback for todo id ${id:-?}"
    return 0
  fi
  title="$(map_get "$SID" "$id")"
  if [ -z "$title" ]; then
    log todo_delete "no title mapping for todo id ${id:-?} — leaving tracker untouched"
    return 0
  fi
  nums="$(nums_for_title "$title")"
  [ -n "$nums" ] || { log todo_delete "no open issue for '$title'"; return 0; }
  printf '%s\n' "$nums" | while IFS= read -r num; do
    isid="$(printf '%s' "$(body_for_num "$num")" | sed -n 's/^session://p' | head -1)"
    imach="$(printf '%s' "$(body_for_num "$num")" | sed -n 's/^machine://p' | head -1)"
    if [ "$isid" = "$SID" ] && [ "$imach" = "$MACHINE" ]; then
      close_issue "$num" "$title" \
        "Withdrawn by creating session ${SID} on ${MACHINE} (${TODAY})."
      log todo_delete "closed issue #$num (created this session) for '$title'"
    else
      log todo_delete "issue #$num for '$title' belongs to session ${isid:-unknown} on ${imach:-unknown} — adopted/foreign, leaving open"
    fi
  done
  return 0
}

case "$TOOL" in
  todo_create)  do_create ;;
  todo_update)  do_update ;;
  todo_complete) do_complete ;;
  todo_delete)  do_delete ;;
esac

exit 0
