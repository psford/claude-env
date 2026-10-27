#!/usr/bin/env bash
# PostToolUse hook: judged by whether it blocks ({"decision": "block"} on stdout) and, when
# it does, whether its reason names the file the fixture expects.
#
# The hook finds the projects directory from its own location (<projects>/claude-env/
# .claude/hooks/), so the driver runs a COPY of it inside a throwaway projects tree: no
# path in the hook exists for tests, and the real card folders are never read.
#
# Fixture contract (a bash file, sourced; setup runs in the throwaway projects tree):
#   setup()          build card folders under ditherware/out/flash/ (or other repos)
#   EXPECT_MATCH     on a BLOCK fixture: text the reason must contain
# Helpers for setup:
#   put REPO REL TEXT    write REPO/out/flash/REL
#   stamp REPO FILE...   add each file's sha256 to REPO's stamp file
#   accept REPO REL...   add each card file, as it is now, to the baseline
set -uo pipefail
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT
mkdir -p "$root/claude-env/.claude/hooks" "$root/claude-env/infrastructure/card-folders"
cp "$hook" "$root/claude-env/.claude/hooks/"
BASELINE="$root/claude-env/infrastructure/card-folders/card-folder-baseline.json"
printf '{"folders": {}}\n' > "$BASELINE"

put() { mkdir -p "$(dirname "$root/$1/out/flash/$2")"; printf '%s' "$3" > "$root/$1/out/flash/$2"; }
stamp() {
  local repo="$1"; shift
  python3 - "$root/$repo/firmware/c100/c/build/emulator-passed.json" "$@" <<'PY'
import hashlib, json, os, sys
path, files = sys.argv[1], sys.argv[2:]
os.makedirs(os.path.dirname(path), exist_ok=True)
data = json.load(open(path)) if os.path.exists(path) else {"stamps": {}}
for f in files:
    data["stamps"][hashlib.sha256(open(f, "rb").read()).hexdigest()] = {"build": f, "harness": "test"}
json.dump(data, open(path, "w"))
PY
}
accept() {
  local repo="$1"; shift
  python3 - "$BASELINE" "$root/$repo/out/flash" "$@" <<'PY'
import hashlib, json, os, sys
path, card, rels = sys.argv[1], sys.argv[2], sys.argv[3:]
data = json.load(open(path))
folder = data["folders"].setdefault(card, {})
for rel in rels:
    folder[rel] = hashlib.sha256(open(os.path.join(card, rel), "rb").read()).hexdigest()
json.dump(data, open(path, "w"))
PY
}

setup() { :; }
EXPECT_MATCH=""
# shellcheck disable=SC1090
source "$fixture"
(cd "$root" && setup) >/dev/null 2>&1

payload=$(printf '{"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "true"}, "cwd": "%s"}' "$root")
out=$(cd /tmp && printf '%s' "$payload" | python3 "$root/claude-env/.claude/hooks/card_folder_watch.py" 2>&1)
rc=$?
blocked=0
printf '%s' "$out" | grep -q '"decision": "block"' && blocked=1
want=0; [ "$expect" = "BLOCK" ] && want=1
ok=1
[ "$rc" -eq 0 ] || ok=0
[ "$blocked" -eq "$want" ] || ok=0
if [ "$want" -eq 1 ] && [ -n "$EXPECT_MATCH" ]; then
  printf '%s' "$out" | grep -qF -- "$EXPECT_MATCH" || ok=0
fi
[ "$ok" -eq 1 ] && exit 0
echo "blocked=$blocked expected=$want rc=$rc :: $out"; exit 1
