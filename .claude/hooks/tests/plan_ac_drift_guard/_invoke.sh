#!/usr/bin/env bash
# Driver for plan_ac_drift_guard.py tests.
#
# The hook shells out to claude-env's real helpers/validate_ac_coverage.py
# at ~/projects/claude-env/helpers/validate_ac_coverage.py (this checkout),
# reading plan-dir files FROM DISK (not staged content) — so the driver just
# needs the plan directory to exist on disk with files staged for detection.
#
# Each fixture is a bash file sourced by this driver, declaring:
#   setup()   # required: write docs/implementation-plans/<slug>/... and stage it
#
# Driver exit code: 0 -> observed rc matched expectation (BLOCK=2, PASS=0).
set -uo pipefail
fixture="$1"; hook="$2"; expect="$3"

setup() { :; }

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
( cd "$repo" && git init -q && git config user.email t@example.com && git config user.name t )
cd "$repo" || exit 1

# shellcheck disable=SC1090
source "$fixture"
setup

out=$(echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m t"}}' | python3 "$hook" 2>&1)
rc=$?

expected=0
[ "$expect" = "BLOCK" ] && expected=2

if [ "$rc" -eq "$expected" ]; then
  exit 0
fi
echo "rc=$rc expected=$expected :: $out"
exit 1
