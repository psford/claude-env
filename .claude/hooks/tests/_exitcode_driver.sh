#!/usr/bin/env bash
# Shared driver for hooks judged on their EXIT CODE (PASS=0 / BLOCK=2).
#
# The runner's default path sends one hardcoded payload: `git commit -m test`.
# A fixture that declares COMMAND or a Write payload is silently ignored on that
# path, so it tests something other than what it says — which is how two
# fixtures written on 2026-08-09 "failed" against hooks that were working.
#
# Fixture contract:
#   setup()                optional: build repo state in $PWD
#   TOOL_NAME              default "Bash"
#   COMMAND                for Bash payloads
#   FILE_PATH, CONTENT     for Write/Edit payloads
#   ENV_VARS=(K=V ...)     optional
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

setup() { :; }
TOOL_NAME="Bash"; COMMAND=""; FILE_PATH=""; CONTENT=""; ENV_VARS=()

repo=$(mktemp -d); trap 'rm -rf "$repo"' EXIT
(
  cd "$repo" && git init -q && git config user.email t@e && git config user.name t \
    && printf 'baseline\n' > README.md && git add README.md && git commit -q -m baseline
) >/dev/null 2>&1
cd "$repo" || exit 1
# shellcheck disable=SC1090
source "$fixture"
setup

payload=$(TOOL_NAME="$TOOL_NAME" COMMAND="$COMMAND" FILE_PATH="$FILE_PATH" \
          CONTENT="$CONTENT" REPO="$repo" python3 - <<'PY'
import json, os
tool = os.environ["TOOL_NAME"]
if tool == "Bash":
    ti = {"command": os.environ["COMMAND"]}
else:
    fp = os.environ["FILE_PATH"]
    if fp and not os.path.isabs(fp):
        fp = os.path.join(os.environ["REPO"], fp)
    ti = {"file_path": fp, "content": os.environ["CONTENT"]}
print(json.dumps({"tool_name": tool, "tool_input": ti, "cwd": os.environ["REPO"]}))
PY
)
if [ "${#ENV_VARS[@]}" -gt 0 ]; then
  out=$(printf '%s' "$payload" | env "${ENV_VARS[@]}" python3 "$hook" 2>&1)
else
  out=$(printf '%s' "$payload" | python3 "$hook" 2>&1)
fi
rc=$?
blocked=0
{ [ "$rc" -eq 2 ] || printf '%s' "$out" | grep -q '"block"'; } && blocked=1
want=0; [ "$expect" = "BLOCK" ] && want=1
[ "$blocked" -eq "$want" ] && exit 0
echo "blocked=$blocked expected=$want rc=$rc :: $out"; exit 1
