#!/usr/bin/env bash
# acceptance.sh — end-to-end acceptance for the polytoken todo bridge
# against REAL gh and the REAL tracker repo. Safe to re-run; every canary
# issue it creates is closed and deleted by the cleanup trap, even on
# mid-script failure.
#
# Uses a SCRATCH state dir (POLYTOKEN_STATE_HOME) so the real per-session
# state on this machine is never touched.
#
# Portability: macOS bash 3.2 subset; no GNU timeout, no GNU stat assumed.
#
# shellcheck disable=SC2015
# ^ `[ cond ] && ok … || bad …` is used throughout: ok()/bad() only printf
# and increment counters and cannot fail, so the A && B || C hazard
# (C running because B failed) does not apply here.

set -u

GH_BIN="${GH_BIN:-gh}"
TODO_REPO="${TODO_REPO:-psford/claude-env}"
LAYER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%s)$$"
SID="acceptance-${STAMP}"
STATE="$(mktemp -d "${TMPDIR:-/tmp}/pt-acceptance.XXXXXX")"
PASS=0
FAIL=0
CANARY_TITLES=""

ok()  { printf '  ok   - %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf '  FAIL - %s\n' "$1"; FAIL=$((FAIL + 1)); }

# Invoked only via the EXIT/INT/TERM trap below.
# shellcheck disable=SC2317
cleanup() {
  if [ -n "$CANARY_TITLES" ]; then
    "$GH_BIN" issue list --repo "$TODO_REPO" --state all \
      --json number,title --limit 200 2>/dev/null \
      | jq -r --arg p "acceptance-${STAMP}" \
        '.[] | select(.title | startswith($p)) | .number' \
      | while IFS= read -r n; do
          [ -n "$n" ] || continue
          "$GH_BIN" issue close "$n" --repo "$TODO_REPO" >/dev/null 2>&1
          "$GH_BIN" issue delete "$n" --repo "$TODO_REPO" --yes >/dev/null 2>&1
        done
  fi
  rm -rf "$STATE"
}
trap cleanup EXIT INT TERM

perm() { # perm <path> -> octal mode, GNU/BSD neutral
  case "$(uname -s)" in
    Darwin) stat -f '%Lp' "$1" 2>/dev/null ;;
    *)      stat -c '%a' "$1" 2>/dev/null ;;
  esac
}

sync_event() { # sync_event <tool> <input-json>
  printf '{"event":"post_tool_use","tool_name":"%s","input":%s}' "$1" "$2" \
    | POLYTOKEN_STATE_HOME="$STATE" GH_BIN="$GH_BIN" TODO_REPO="$TODO_REPO" \
      /bin/bash "$LAYER_DIR/hooks/todo-sync.sh"
}

issue_json() { # issue_json -> open todo issues as a jq array
  "$GH_BIN" issue list --repo "$TODO_REPO" --label todo --state open \
    --json number,title,body,labels --limit 200 2>/dev/null
}

count_open_titled() { # count_open_titled <title>
  issue_json | jq --arg t "$1" '[.[] | select(.title == $t)] | length'
}

# gh mutations land asynchronously (the sync hook is fire-and-forget), so
# assertions POLL for the reflected state instead of sleeping a fixed gap.
assert_open_count() { # assert_open_count <want> <title> <okmsg> <badmsg>
  local i=0 got=""
  while [ "$i" -lt 30 ]; do
    got="$(count_open_titled "$2")"
    if [ "$got" = "$1" ]; then
      ok "$3"
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  bad "$4 (got ${got:-0} open)"
  return 0
}

wait_labels() { # wait_labels <title> <want-label> -> 0 once reflected
  local i=0 got=""
  while [ "$i" -lt 20 ]; do
    got="$(issue_json | jq -r --arg t "$1" \
      '.[] | select(.title == $t) | .labels[]?.name' | grep -cx "$2" || true)"
    [ "$got" = "1" ] && return 0
    sleep 0.5
    i=$((i + 1))
  done
  return 1
}

seed_todo() { # seed_todo <id> <title>  (session todo store in scratch state)
  mkdir -p "$STATE/sessions-v1/$SID/todos"
  printf '{"id":%s,"title":"%s","description":"acceptance","status":"pending","dependencies":[]}' \
    "$1" "$2" > "$STATE/sessions-v1/$SID/todos/$1.json"
}

printf 'polytoken layer acceptance — repo %s, session %s\n\n' "$TODO_REPO" "$SID"

# ---------------------------------------------------------------- prereqs
command -v "$GH_BIN" >/dev/null 2>&1 || { printf 'gh not found\n'; exit 1; }
command -v jq >/dev/null 2>&1 || { printf 'jq not found\n'; exit 1; }
"$GH_BIN" auth status >/dev/null 2>&1 || { printf 'gh not authenticated\n'; exit 1; }
ok "prerequisites (gh auth, jq)"

printf '%s' "$SID" > "$STATE/todo-session.current"

# --------------------------------------------------- create + dedupe (AC.3)
A="acceptance-${STAMP}-alpha"
seed_todo 1 "$A"
sync_event todo_create "{\"title\":\"$A\",\"description\":\"acceptance canary A\"}" \
  || bad "create event exited nonzero"
assert_open_count 1 "$A" "create round-trips: one open issue for '$A'" \
  "expected 1 open issue for '$A'"

sync_event todo_create "{\"title\":\"$A\",\"description\":\"dupe\"}"
sleep 3  # let both syncs settle before the dedupe assertion
assert_open_count 1 "$A" "same-title create dedupes" "dedupe failed"

# ------------------------------------------------------- labels + rename
# The real daemon mutates the session todo store BEFORE post_tool_use
# fires, so the seed file is rewritten to the post-tool state first.
seed_todo 1 "$A" "in_progress"
sync_event todo_update "{\"id\":1,\"status\":\"in_progress\"}"
if wait_labels "$A" "in-progress"; then ok "in-progress label added on status transition"; else bad "in-progress label missing"; fi

B="acceptance-${STAMP}-beta"
seed_todo 1 "$B" "in_progress"
sync_event todo_update "{\"id\":1,\"title\":\"$B\"}"
assert_open_count 1 "$B" "rename round-trips via gh issue edit" "rename failed"

# ------------------------------------------------------- complete (AC.4)
seed_todo 1 "$B" "done"
sync_event todo_complete '{"id":1}'
assert_open_count 0 "$B" "complete closes the tracked issue" "complete did not close"

# ------------------------------------------------ delete semantics (risk #1)
C="acceptance-${STAMP}-gamma"
seed_todo 2 "$C"
sync_event todo_create "{\"title\":\"$C\",\"description\":\"created this session\"}"
assert_open_count 1 "$C" "gamma canary created" "gamma canary missing"
sync_event todo_delete '{"id":2}'
assert_open_count 0 "$C" "delete of created-this-session closes the issue" "delete-of-created did not close"

D="acceptance-${STAMP}-delta"
seed_todo 3 "$D"
sync_event todo_create "{\"title\":\"$D\",\"description\":\"adopted stand-in\"}"
assert_open_count 1 "$D" "delta canary created" "delta canary missing"
dnum="$(issue_json | jq -r --arg t "$D" '.[] | select(.title == $t) | .number' | head -1)"
"$GH_BIN" issue edit "$dnum" --repo "$TODO_REPO" \
  --body "adopted stand-in

session:some-earlier-session
machine:some-other-machine
date:2026-09-30" >/dev/null 2>&1
sync_event todo_delete '{"id":3}'
assert_open_count 1 "$D" "delete of adopted issue leaves it open" "adopted issue was closed"

# --------------------------------------------------- todo_list is free
LOG="$STATE/todo-sync.log"
before=0
[ -f "$LOG" ] && before="$(wc -l < "$LOG" | tr -d ' ')"
sync_event todo_list '{}'
after=0
[ -f "$LOG" ] && after="$(wc -l < "$LOG" | tr -d ' ')"
[ "$before" = "$after" ] && ok "todo_list writes no log line" || bad "todo_list logged"

# ---------------------------------------------------- restore (AC.5)
E="acceptance-${STAMP}-epsilon"
seed_todo 4 "$E"
sync_event todo_create "{\"title\":\"$E\",\"description\":\"restore canary\"}"
assert_open_count 1 "$E" "epsilon canary created" "epsilon canary missing"
OUT="$(printf '{"event":"session_start","matcher_subject":"session_start","session_id":"%s"}' "$SID" \
  | POLYTOKEN_STATE_HOME="$STATE" GH_BIN="$GH_BIN" TODO_REPO="$TODO_REPO" \
    /bin/bash "$LAYER_DIR/hooks/todo-restore.sh")"
echo "$OUT" | jq -e '.outcome == "allow"' >/dev/null 2>&1 \
  && ok "restore emits valid allow JSON" || bad "restore output invalid: $OUT"
total="$(issue_json | jq 'length')"
ctx="$(echo "$OUT" | jq -r '.additional_context // empty')"
if [ "$total" -le 30 ] 2>/dev/null; then
  case "$ctx" in *"$E"*) ok "restore context lists the tracked todos" ;; *) bad "restore context missing canary" ;; esac
else
  case "$ctx" in *"+ "*more*|*"more open todos"*) ok "restore context caps at 30 with +N note" ;; *) bad "restore cap note missing" ;; esac
fi
sid_read="$(cat "$STATE/todo-session.current" 2>/dev/null)"
[ "$sid_read" = "$SID" ] && ok "restore records the session id" || bad "session file wrong: ${sid_read:-unset}"

# -------------------------------------------- sabotage timing (AC.5/AC.7)
T0=$(date +%s)
OUT2="$(printf '{"event":"session_start","session_id":"%s"}' "$SID" \
  | POLYTOKEN_STATE_HOME="$STATE" GH_BIN=/bin/false \
    /bin/bash "$LAYER_DIR/hooks/todo-restore.sh")"
T1=$(date +%s)
echo "$OUT2" | jq -e '.outcome == "allow"' >/dev/null 2>&1 \
  && ok "sabotaged restore still emits valid allow" || bad "sabotaged restore invalid: $OUT2"
[ $((T1 - T0)) -le 5 ] && ok "sabotaged restore within ~5s (took $((T1-T0))s)" \
                       || bad "sabotaged restore too slow: $((T1-T0))s"

HANG="$STATE/hang-gh.sh"
printf '#!/usr/bin/env bash\nsleep 30\n' > "$HANG"
chmod +x "$HANG"
T0=$(date +%s)
OUT3="$(printf '{"event":"session_start","session_id":"%s"}' "$SID" \
  | POLYTOKEN_STATE_HOME="$STATE" GH_BIN="$HANG" \
    /bin/bash "$LAYER_DIR/hooks/todo-restore.sh")"
T1=$(date +%s)
echo "$OUT3" | jq -e '.outcome == "allow"' >/dev/null 2>&1 \
  && ok "hung gh: restore fails open" || bad "hung gh broke restore: $OUT3"
[ $((T1 - T0)) -le 8 ] && ok "hung gh killed within budget (took $((T1-T0))s)" \
                      || bad "hung gh made restore slow: $((T1-T0))s"

# ------------------------------------------------------ secrets perms (AC.2)
SEC="$HOME/.config/polytoken/secrets"
if [ -d "$SEC" ]; then
  [ "$(perm "$SEC")" = "700" ] && ok "secrets dir is 0700" || bad "secrets dir is $(perm "$SEC"), want 700"
  badfile=""
  for f in "$SEC"/*; do
    [ "$(perm "$f")" = "600" ] || badfile="$badfile $f($(perm "$f"))"
  done
  [ -z "$badfile" ] && ok "secrets files are 0600" || bad "bad perms:$badfile"
else
  bad "secrets dir $SEC missing (run bootstrap first)"
fi

CANARY_TITLES="set"  # cleanup sweep keys off the title prefix
printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" = 0 ] || exit 1
exit 0
