#!/usr/bin/env bash
# Driver for main_branch_guard.py tests.
#
# Each fixture is a bash file sourced by this driver. It declares:
#   setup()          # optional: build repo state (files, commits) in $PWD
#   COMMAND          # the Bash command string to feed the hook as tool_input.command
#   ENV_VARS=(K=V ..)# optional: env vars exported before invoking the hook
#   PROCESS_CWD      # optional: run the hook FROM this directory instead of the
#                    # scratch repo. Hooks run with the process working directory
#                    # set to the session's repo, which is not necessarily the
#                    # repo the command targets. Without this axis every fixture
#                    # has process cwd == payload cwd, and a guard that reads
#                    # os.getcwd() instead of the payload looks correct.
#
# The fixture runs inside a fresh scratch git repo (already `git init`'d with
# one baseline commit) so git diff/status calculations have a real HEAD to
# compare against.
#
# Driver exit code: 0 → observed rc matched expectation (BLOCK=2, PASS=0/other-non-2).
set -uo pipefail
fixture="$1"; hook="$2"; expect="$3"

setup() { :; }
COMMAND=""
ENV_VARS=()
PROCESS_CWD=""

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
( cd "$repo" && git init -q && git config user.email t@example.com && git config user.name t \
  && printf 'baseline\n' > README.md && git add README.md && git commit -q -m baseline )

cd "$repo" || exit 1
# shellcheck disable=SC1090
source "$fixture"
setup

if [ -z "$COMMAND" ]; then
  echo "fixture did not set COMMAND"
  exit 1
fi

payload=$(python3 - "$COMMAND" "$repo" <<'PYEOF'
import json, sys
print(json.dumps({"tool_name": "Bash", "tool_input": {"command": sys.argv[1]}, "cwd": sys.argv[2]}))
PYEOF
)

env_prefix=()
for kv in "${ENV_VARS[@]+"${ENV_VARS[@]}"}"; do
  env_prefix+=("$kv")
done

run_from="${PROCESS_CWD:-$repo}"

if [ "${#env_prefix[@]}" -gt 0 ]; then
  out=$(cd "$run_from" && echo "$payload" | env "${env_prefix[@]}" python3 "$hook" 2>&1)
else
  out=$(cd "$run_from" && echo "$payload" | python3 "$hook" 2>&1)
fi
rc=$?

expected=0
[ "$expect" = "BLOCK" ] && expected=2

if [ "$rc" -eq "$expected" ]; then
  exit 0
fi
echo "rc=$rc expected=$expected :: $out"
exit 1
