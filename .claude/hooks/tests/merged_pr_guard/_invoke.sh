#!/usr/bin/env bash
# merged_pr_guard shells out to `gh`, so the fixture puts a STUB gh on PATH.
# Without that the blocking path needs network and auth, and an untestable
# blocking path is how this guard reached 2026-08-09 never having been watched
# refuse anything -- while being one of only seven guards that can refuse at all.
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

setup() { :; }
COMMAND=""
GH_STATE=""      # what the stub reports: MERGED | OPEN | CLOSED
GH_NUMBER="7"

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
( cd "$repo" && git init -q -b feature/x && git config user.email t@e && git config user.name t \
  && printf 'x\n' > R && git add -A && git commit -q -m base )
cd "$repo" || exit 1
# shellcheck disable=SC1090
source "$fixture"
setup

if [ -n "$GH_STATE" ]; then
  mkdir -p "$repo/.stub"
  cat > "$repo/.stub/gh" <<STUB
#!/usr/bin/env bash
# Emulate gh faithfully, which matters: with --jq gh does the extraction itself
# and returns a BARE string, not JSON. A stub that always printed the object
# made this guard look broken when it was fine -- a false defect, caught only
# by reading how the hook actually calls gh.
for a in "\$@"; do
  if [ "\$a" = ".state" ]; then echo "$GH_STATE"; exit 0; fi
done
echo '{"state":"$GH_STATE","number":$GH_NUMBER}'
STUB
  chmod +x "$repo/.stub/gh"
  export PATH="$repo/.stub:$PATH"
fi

payload=$(COMMAND="$COMMAND" REPO="$repo" python3 - <<'PY'
import json, os
print(json.dumps({"tool_name": "Bash",
                  "tool_input": {"command": os.environ["COMMAND"]},
                  "cwd": os.environ["REPO"]}))
PY
)
out=$(printf '%s' "$payload" | python3 "$hook" 2>&1); rc=$?
expected=0; [ "$expect" = "BLOCK" ] && expected=2
[ "$rc" -eq "$expected" ] && exit 0
echo "rc=$rc expected=$expected :: $out"
exit 1
