#!/usr/bin/env bash
# Driver for shared_rules_link_guard.py tests.
#
# The runner's DEFAULT path is not usable here: it sends one hardcoded
# `git commit -m test` payload with no `cwd` key, and ignores COMMAND and
# setup() entirely. This guard's whole job is to inspect the repo the command
# targets, so a payload with no cwd tests nothing -- it fell back to claude-env,
# which is healthy, and three BLOCK fixtures passed silently.
#
# Each fixture is a bash file sourced by this driver. It declares:
#   setup()          # optional: build repo state (files, commits) in $PWD
#   COMMAND          # the Bash command string to feed the hook as tool_input.command
#   ENV_VARS=(K=V ..)# optional: env vars exported before invoking the hook
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

if [ "${#env_prefix[@]}" -gt 0 ]; then
  out=$(echo "$payload" | env "${env_prefix[@]}" python3 "$hook" 2>&1)
else
  out=$(echo "$payload" | python3 "$hook" 2>&1)
fi
rc=$?

expected=0
[ "$expect" = "BLOCK" ] && expected=2

if [ "$rc" -eq "$expected" ]; then
  exit 0
fi
echo "rc=$rc expected=$expected :: $out"
exit 1
