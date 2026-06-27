#!/usr/bin/env bash
# Driver: stage a decisions.md (AC4.2 DESCOPED) + the fixture as a plan file.
set -uo pipefail
fixture="$1"; hook="$2"; expect="$3"
repo=$(mktemp -d); trap 'rm -rf "$repo"' EXIT
( cd "$repo" && git init -q && mkdir -p docs/implementation-plans/x )
cat > "$repo/docs/decisions.md" <<'DEC'
## emphasize sizing
2026-06-26: overview-single-screen.AC4.2 DESCOPED — incompatible with the fill.
DEC
cp "$fixture" "$repo/docs/implementation-plans/x/case.md"
( cd "$repo" && git add docs/decisions.md docs/implementation-plans/x/case.md >/dev/null 2>&1 )
out=$(cd "$repo" && echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m t"}}' | python3 "$hook" 2>&1)
rc=$?
expected=0; [ "$expect" = "BLOCK" ] && expected=2
[ "$rc" -eq "$expected" ] && exit 0
echo "rc=$rc expected=$expected :: $out"; exit 1
