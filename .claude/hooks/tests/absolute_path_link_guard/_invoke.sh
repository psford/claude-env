#!/usr/bin/env bash
# A Stop hook. Its input is a transcript path, not a command, so the fixture
# supplies REPLY and the driver writes a one-line JSONL transcript for it to
# read -- the same shape Claude Code writes.
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

REPLY=""
# shellcheck disable=SC1090
source "$fixture"

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
transcript="$tmp/t.jsonl"
REPLY="$REPLY" python3 - "$transcript" <<'PY'
import json, os, sys
json.dump({"type": "assistant",
           "message": {"role": "assistant",
                       "content": [{"type": "text", "text": os.environ["REPLY"]}]}},
          open(sys.argv[1], "w"))
open(sys.argv[1], "a").write("\n")
PY

out=$(printf '{"transcript_path":"%s"}' "$transcript" | python3 "$hook" 2>&1); rc=$?
# This guard signals refusal with {"decision":"block"} and exit 0, not exit 2.
blocked=0
printf '%s' "$out" | grep -q '"block"' && blocked=1
want=0; [ "$expect" = "BLOCK" ] && want=1
[ "$blocked" -eq "$want" ] && exit 0
echo "blocked=$blocked expected=$want rc=$rc :: $out"
exit 1
