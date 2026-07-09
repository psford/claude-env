#!/usr/bin/env bash
# Driver for design_signoff_guard.py tests.
#
# The hook reads current branch (must start with feat/) + staged files +
# tracked/staged docs/design-plans/*.md content — none of which the
# default synthetic-payload path in run-hook-tests.sh can set up. Each
# fixture is a bash file sourced by this driver, declaring:
#   BRANCH            # default "feat/emphasis-sizing"
#   setup()           # required: write + stage repo state in $PWD
#   COMMAND           # default "git commit -m t"
#
# Driver exit code: 0 -> observed rc matched expectation (BLOCK=2, PASS=0).
set -uo pipefail
fixture="$1"; hook="$2"; expect="$3"

BRANCH="feat/emphasis-sizing"
COMMAND="git commit -m t"
setup() { :; }

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
( cd "$repo" && git init -q && git config user.email t@example.com && git config user.name t )

cd "$repo" || exit 1
# Seed a baseline commit so `git checkout -b` and HEAD-relative lookups work.
printf 'baseline\n' > README.md
git add README.md
git commit -q -m baseline >/dev/null

# shellcheck disable=SC1090
source "$fixture"

git checkout -q -b "$BRANCH"
setup

payload='{"tool_name":"Bash","tool_input":{"command":"'"${COMMAND//\"/\\\"}"'"}}'
out=$(echo "$payload" | python3 "$hook" 2>&1)
rc=$?

expected=0
[ "$expect" = "BLOCK" ] && expected=2

if [ "$rc" -eq "$expected" ]; then
  exit 0
fi
echo "rc=$rc expected=$expected :: $out"
exit 1
