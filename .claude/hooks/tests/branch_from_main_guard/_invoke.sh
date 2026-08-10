#!/usr/bin/env bash
# Needs origin/main and origin/develop refs: the guard compares them to decide
# whether branching from main would strand work. A scratch repo has no remote,
# so without these the guard correctly does nothing — which read as "broken"
# for three probes on 2026-08-09 before the cause was found.
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"
COMMAND=""; DEVELOP_AHEAD=1; START_ON="main"
repo=$(mktemp -d); trap 'rm -rf "$repo"' EXIT
(
  cd "$repo" && git init -q -b main && git config user.email t@e && git config user.name t
  printf 'x\n' > R && git add -A && git commit -q -m base
  git update-ref refs/remotes/origin/main HEAD
  git checkout -q -b develop
) >/dev/null 2>&1
# shellcheck disable=SC1090
source "$fixture"
(
  cd "$repo"
  if [ "$DEVELOP_AHEAD" -eq 1 ]; then
    printf 'y\n' > S && git add -A && git commit -q -m "feat: work on develop"
  fi
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q "$START_ON"
) >/dev/null 2>&1
payload=$(COMMAND="$COMMAND" REPO="$repo" python3 -c '
import json, os
print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["COMMAND"]},"cwd":os.environ["REPO"]}))')
out=$(printf '%s' "$payload" | python3 "$hook" 2>&1); rc=$?
want=0; [ "$expect" = "BLOCK" ] && want=2
[ "$rc" -eq "$want" ] && exit 0
echo "rc=$rc expected=$want :: $out"; exit 1
