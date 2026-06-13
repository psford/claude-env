#!/usr/bin/env bash
# Tests for helpers/sync-claude-md.sh — the shared-CLAUDE.md assembler.
#
# Each test builds an isolated fake claude-env (fragments) + fake repo
# (config + CLAUDE.local.md) under a temp dir, runs the script with
# CLAUDE_ENV_ROOT pointed at the fake fragments, and asserts output.
#
# Usage: bash helpers/tests/test_sync_claude_md.sh
# Exit 0 if all pass, 1 if any fail.
set -uo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SELF_DIR/../sync-claude-md.sh"

pass=0; fail=0
ok()  { echo "  ✓ $1"; pass=$((pass+1)); }
no()  { echo "  ✗ $1"; echo "     $2" | sed 's/^/     /'; fail=$((fail+1)); }

# Build a fake claude-env + repo. Echoes the workspace dir.
make_workspace() {
  local ws; ws=$(mktemp -d)
  mkdir -p "$ws/env/shared/claude-md" "$ws/repo/.claude"
  printf '## Principles\nWork on %s, ship to %s.\n' '{{WORKING_BRANCH}}' '{{PRODUCTION_BRANCH}}' \
    > "$ws/env/shared/claude-md/00-universal.md"
  printf '## Stack\nWindows service rules.\n' \
    > "$ws/env/shared/claude-md/stack-windows-service.md"
  printf '# MyRepo\nProject-specific contracts here.\n' \
    > "$ws/repo/CLAUDE.local.md"
  echo "$ws"
}

echo "── sync-claude-md.sh ──"

# ---------------------------------------------------------------------------
# Test 1: basic assembly — header + fragment + local, in order.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" 2>&1); rc=$?
gen="$ws/repo/CLAUDE.md"
if [ "$rc" -ne 0 ]; then no "basic assembly" "exit $rc: $out"
elif [ ! -f "$gen" ]; then no "basic assembly" "no CLAUDE.md written"
elif ! grep -q "DO NOT EDIT" "$gen"; then no "basic assembly" "missing generated header"
elif ! grep -q "Work on develop, ship to main." "$gen"; then no "basic assembly" "fragment/vars not substituted: $(cat "$gen")"
elif ! grep -q "Project-specific contracts here." "$gen"; then no "basic assembly" "CLAUDE.local.md not appended"
else
  # order: header line precedes fragment precedes local
  hl=$(grep -n "DO NOT EDIT" "$gen" | head -1 | cut -d: -f1)
  fl=$(grep -n "Work on develop" "$gen" | head -1 | cut -d: -f1)
  ll=$(grep -n "Project-specific" "$gen" | head -1 | cut -d: -f1)
  if [ "$hl" -lt "$fl" ] && [ "$fl" -lt "$ll" ]; then ok "basic assembly (header→fragment→local, vars substituted)"
  else no "basic assembly" "wrong order h=$hl f=$fl l=$ll"; fi
fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2: multiple fragments included in listed order.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal", "stack-windows-service"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
gen="$ws/repo/CLAUDE.md"
if grep -q "Windows service rules." "$gen" && \
   [ "$(grep -n 'Principles' "$gen" | head -1 | cut -d: -f1)" -lt "$(grep -n 'Stack' "$gen" | head -1 | cut -d: -f1)" ]; then
  ok "multiple fragments in listed order"
else no "multiple fragments" "$(cat "$gen")"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 3: --check exits 0 when in sync, non-zero when drifted.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1   # generate
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" >/dev/null 2>&1; rc_sync=$?
echo "drifted by hand" >> "$ws/repo/CLAUDE.md"
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" >/dev/null 2>&1; rc_drift=$?
if [ "$rc_sync" -eq 0 ] && [ "$rc_drift" -ne 0 ]; then ok "--check: 0 in sync, non-zero on drift"
else no "--check drift detection" "in-sync rc=$rc_sync drift rc=$rc_drift"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 4: missing fragment is a hard error (non-zero, names the fragment).
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["does-not-exist"], "vars": {} }
JSON
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" 2>&1); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "does-not-exist"; then ok "missing fragment errors and names it"
else no "missing fragment" "rc=$rc out=$out"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 5: --check is read-only (does not write/modify CLAUDE.md).
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
printf 'sentinel-untouched\n' > "$ws/repo/CLAUDE.md"
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" >/dev/null 2>&1
if grep -q "sentinel-untouched" "$ws/repo/CLAUDE.md"; then ok "--check does not modify CLAUDE.md"
else no "--check read-only" "file was modified"; fi
rm -rf "$ws"

echo ""
if [ "$fail" -eq 0 ]; then echo "ALL $pass SYNC TESTS PASSED"; exit 0
else echo "$fail of $((pass+fail)) SYNC TESTS FAILED"; exit 1; fi
