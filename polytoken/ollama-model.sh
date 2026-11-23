#!/usr/bin/env bash
# ollama-model.sh — choose which model the LAN Ollama server holds in VRAM.
#
# `ollama serve` has no "start with this model" flag. The server starts with
# nothing loaded, loads whichever model a request names, and unloads idle
# models when VRAM runs short. "Launch Ollama with model X" is therefore
# three things: the server is up, X is in its model store, and X is loaded.
# This script does the last two over the HTTP API, so it runs unchanged on
# the MacBook and in WSL and needs no shell on the Windows box.
#
# Usage:
#   ollama-model.sh list                 models in the server's store; * = loaded
#   ollama-model.sh status               what is in memory: size, GPU share, context
#   ollama-model.sh use <model>          pull <model> if it is missing, unload the
#                                        others, load it and keep it loaded
#   ollama-model.sh use <model> --keep   the same, but leave loaded models alone
#   ollama-model.sh unload [<model>]     unload one model, or every model
#
# `use` unloads the other models, so do not run it while another job is using
# one of them: that job would reload its model on its next request.
#
# Server address, first match wins:
#   1. $OLLAMA_URL
#   2. ~/.config/polytoken/ollama-url — the per-machine file the Polytoken
#      config template reads (a trailing /v1 is ignored here)
#   3. http://127.0.0.1:11434
#
# Exit codes: 0 done; 1 usage, unreachable server or API error;
#             2 the model loaded but is not fully on the GPU.
#
# Written for macOS's bash 3.2 as well as Linux. Needs curl and jq.

set -u

URL_FILE="$HOME/.config/polytoken/ollama-url"
TEMPLATE="$(dirname "$0")/config.template.yaml"
BODY=""
CODE=""

log() { printf '%s\n' "$*" >&2; }
die() { log "ollama-model: $*"; exit 1; }

usage() {
  sed -n '/^# Usage:/,/^# Written for/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//' >&2
  exit 1
}

resolve_url() {
  local u="${OLLAMA_URL:-}"
  if [ -z "$u" ] && [ -r "$URL_FILE" ]; then
    u="$(tr -d '[:space:]' < "$URL_FILE")"
  fi
  [ -n "$u" ] || u="http://127.0.0.1:11434"
  u="${u%/}"
  u="${u%/v1}"
  printf '%s' "$u"
}

# call <path> [json-body] [timeout-seconds] — sets BODY and CODE.
call() {
  local path="$1" data="${2:-}" tmo="${3:-20}" out
  if [ -n "$data" ]; then
    out="$(curl -sS -m "$tmo" -w '\n%{http_code}' -H 'Content-Type: application/json' \
      -d "$data" "$BASE$path")" || return 1
  else
    out="$(curl -sS -m "$tmo" -w '\n%{http_code}' "$BASE$path")" || return 1
  fi
  CODE="${out##*$'\n'}"
  BODY="${out%$'\n'*}"
}

# Fail with the server's own error text when a call did not return 200.
expect_ok() {
  local what="$1" err
  [ "$CODE" = "200" ] && return 0
  err="$(printf '%s' "$BODY" | jq -r '.error // empty' 2>/dev/null)"
  die "$what failed (HTTP $CODE): ${err:-$BODY}"
}

# A name without a tag means :latest, the way Ollama reads it.
canon() {
  case "$1" in
    *:*) printf '%s' "$1" ;;
    *) printf '%s:latest' "$1" ;;
  esac
}

require_server() {
  call /api/version "" 5 || die "Ollama is not answering at $BASE. It runs natively on the Windows box and has to be started there."
  expect_ok "reading the server version"
}

loaded_names() {
  call /api/ps || die "could not read the loaded models from $BASE"
  expect_ok "reading the loaded models"
  printf '%s' "$BODY" | jq -r '.models // [] | .[].name'
}

in_store() {
  call /api/tags || die "could not read the model list from $BASE"
  expect_ok "reading the model list"
  printf '%s' "$BODY" | jq -e --arg m "$1" '.models // [] | map(.name) | index($m) != null' >/dev/null
}

print_status() {
  call /api/ps || die "could not read the loaded models from $BASE"
  expect_ok "reading the loaded models"
  printf '%s' "$BODY" | jq -r '
    (.models // []) as $m
    | if ($m | length) == 0 then "nothing is loaded"
      else (["MODEL", "IN MEMORY", "ON GPU", "CONTEXT"],
            ($m[] | [.name,
                     (((.size / 1e8 | round) / 10 | tostring) + " GB"),
                     ((if .size > 0 then (.size_vram * 100 / .size | floor) else 0 end | tostring) + "%"),
                     (.context_length // "?" | tostring)]))
           | @tsv
      end' | column -t -s "$(printf '\t')"
}

cmd_list() {
  local tags
  require_server
  call /api/tags || die "could not read the model list from $BASE"
  expect_ok "reading the model list"
  tags="$BODY"
  call /api/ps || die "could not read the loaded models from $BASE"
  expect_ok "reading the loaded models"
  jq -rn --argjson t "$tags" --argjson p "$BODY" '
    ($p.models // [] | map(.name)) as $loaded
    | (["", "MODEL", "ON DISK", "PARAMS", "QUANT"],
       ($t.models // [] | sort_by(.name)[]
        | [(if (.name as $n | $loaded | index($n)) != null then "*" else "-" end),
           .name,
           (((.size / 1e8 | round) / 10 | tostring) + " GB"),
           (.details.parameter_size // "?"),
           (.details.quantization_level // "?")]))
    | @tsv' | column -t -s "$(printf '\t')"
}

pull_model() {
  local m="$1" line failed=0
  log "$m is not on the server yet; pulling it"
  # One jq process reads the whole progress stream and prints a line only
  # when the step or its ten-percent mark changes.
  curl -sS -N -m 14400 -H 'Content-Type: application/json' \
    -d "$(jq -cn --arg m "$m" '{model: $m, stream: true}')" "$BASE/api/pull" |
    jq -rn --unbuffered '
      foreach inputs as $l ({last: "", out: null};
        if $l.error then .out = "ERROR " + ($l.error | tostring)
        else (($l.status // "")
              + (if ($l.total // 0) > 0
                 then " " + ((($l.completed // 0) * 10 / $l.total | floor) * 10 | tostring) + "%"
                 else "" end)) as $s
             | if $s != .last then .last = $s | .out = $s else .out = null end
        end;
        .out // empty)' |
    while IFS= read -r line; do
      log "  $line"
      case "$line" in "ERROR "*) failed=1 ;; esac
      [ "$failed" = 0 ] || exit 1
    done || die "pull of $m failed"
  in_store "$m" || die "pull of $m ended, but the server still does not list it"
}

unload_model() {
  local m="$1" i=0
  call /api/generate "$(jq -cn --arg m "$m" '{model: $m, keep_alive: 0, stream: false}')" 120 \
    || die "could not reach $BASE to unload $m"
  expect_ok "unloading $m"
  while loaded_names | grep -qxF "$m"; do
    i=$((i + 1))
    [ "$i" -le 60 ] || die "$m is still loaded after 60 seconds; a request may be using it"
    sleep 1
  done
  log "unloaded $m"
}

cmd_unload() {
  local target="${1:-}" names n
  require_server
  names="$(loaded_names)"
  if [ -z "$names" ]; then
    log "nothing is loaded"
    return 0
  fi
  if [ -n "$target" ]; then
    target="$(canon "$target")"
    printf '%s\n' "$names" | grep -qxF "$target" || die "$target is not loaded"
    unload_model "$target"
  else
    printf '%s\n' "$names" | while IFS= read -r n; do unload_model "$n" || exit 1; done || exit 1
  fi
}

# Say so when the Polytoken template has no entry that sends this model name.
polytoken_note() {
  local m="$1" p
  [ -r "$TEMPLATE" ] || return 0
  sed -n 's/^[[:space:]]*provider_name:[[:space:]]*//p' "$TEMPLATE" |
    while IFS= read -r p; do
      [ "$(canon "$p")" = "$m" ] && exit 9
    done
  [ "$?" = 9 ] && return 0
  log "note: Polytoken has no entry for $m. Add one under models: in $TEMPLATE (provider: ollama, provider_name: $m)."
}

cmd_use() {
  local m="${1:-}" keep="${2:-}" names n gpu
  [ -n "$m" ] || usage
  case "$keep" in "" | --keep) ;; *) usage ;; esac
  m="$(canon "$m")"
  require_server
  in_store "$m" || pull_model "$m"
  if [ "$keep" != "--keep" ]; then
    names="$(loaded_names)"
    if [ -n "$names" ]; then
      printf '%s\n' "$names" | while IFS= read -r n; do
        [ "$n" = "$m" ] || unload_model "$n" || exit 1
      done || exit 1
    fi
  fi
  log "loading $m"
  call /api/generate "$(jq -cn --arg m "$m" '{model: $m, keep_alive: -1, stream: false}')" 600 \
    || die "the load request for $m did not complete"
  expect_ok "loading $m"
  print_status
  gpu="$(printf '%s' "$BODY" | jq -r --arg m "$m" \
    '.models // [] | map(select(.name == $m)) | .[0] | if . == null then "missing" elif .size > 0 then (.size_vram * 100 / .size | floor) else 0 end')"
  [ "$gpu" != "missing" ] || die "$m answered the load request but is not in the loaded list"
  polytoken_note "$m"
  if [ "$gpu" -lt 100 ]; then
    log "ollama-model: $m is only ${gpu}% on the GPU; the rest runs on the CPU and will be slow. It needs more free VRAM or a smaller context."
    exit 2
  fi
}

command -v curl >/dev/null 2>&1 || die "curl is required"
command -v jq >/dev/null 2>&1 || die "jq is required"
BASE="$(resolve_url)"

case "${1:-}" in
  list) cmd_list ;;
  status) require_server; print_status ;;
  use) shift; cmd_use "$@" ;;
  unload) shift; cmd_unload "$@" ;;
  *) usage ;;
esac
