#!/usr/bin/env bash
# Stop hook: judged by whether it sends the reply back ({"decision": "block"} on stdout).
#
# Fixture contract (a bash file, sourced):
#   MESSAGE            the reply's text: the last assistant message in the transcript
#   TOOL_CALL_AFTER    optional, 1: an assistant entry with only a tool call follows it,
#                      as when a reply's text came before its last tool use
#   NO_TRANSCRIPT      optional, 1: the payload names no transcript
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

MESSAGE=""; TOOL_CALL_AFTER=""; NO_TRANSCRIPT=""
# shellcheck disable=SC1090
source "$fixture"

work=$(mktemp -d)
elsewhere=$(mktemp -d)
trap 'rm -rf "$work" "$elsewhere"' EXIT
payload=$(MESSAGE="$MESSAGE" TOOL_CALL_AFTER="$TOOL_CALL_AFTER" NO_TRANSCRIPT="$NO_TRANSCRIPT" WORK="$work" python3 - <<'PY'
import json, os
path = os.path.join(os.environ["WORK"], "session.jsonl")
entries = [{"type": "user", "message": {"role": "user", "content": "go"}}]
if os.environ["MESSAGE"]:
    entries.append({"type": "assistant", "message": {"role": "assistant",
                    "content": [{"type": "text", "text": os.environ["MESSAGE"]}]}})
if os.environ["TOOL_CALL_AFTER"]:
    entries.append({"type": "assistant", "message": {"role": "assistant",
                    "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}})
with open(path, "w") as f:
    f.write("\n".join(json.dumps(e) for e in entries) + "\n")
payload = {"hook_event_name": "Stop", "stop_hook_active": False}
if not os.environ["NO_TRANSCRIPT"]:
    payload["transcript_path"] = path
print(json.dumps(payload))
PY
)
out=$(cd "$elsewhere" && printf '%s' "$payload" | python3 "$hook" 2>&1)
rc=$?
blocked=0
printf '%s' "$out" | grep -q '"decision": "block"' && blocked=1
want=0; [ "$expect" = "BLOCK" ] && want=1
[ "$rc" -eq 0 ] && [ "$blocked" -eq "$want" ] && exit 0
echo "blocked=$blocked expected=$want rc=$rc :: $out"; exit 1
