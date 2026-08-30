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
# Test 2: a fragment carrying no substitutions is LINKED, not copied (AC1, AC3).
#
# This test used to assert stack-windows-service's text appeared inside the
# generated CLAUDE.md. It does not any more, and that is the point of CE-5.1:
# a fragment with no {{VARS}} is byte-identical in every repo, so copying it
# creates N files that can disagree. The copy is what drift needs to exist.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal", "stack-windows-service"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
gen="$ws/repo/CLAUDE.md"
link="$ws/repo/.claude/rules/stack-windows-service.md"
if [ ! -L "$link" ]; then no "var-free fragment is linked" "$link is not a symlink"
elif grep -q "Windows service rules." "$gen"; then
  no "var-free fragment is linked" "text is ALSO copied into CLAUDE.md — two sources exist"
elif [ ! -r "$link" ]; then no "var-free fragment is linked" "link does not resolve to readable content"
elif [ "$(cat "$link")" != "$(cat "$ws/env/shared/claude-md/stack-windows-service.md")" ]; then
  no "var-free fragment is linked" "link content differs from source"
else ok "a var-free fragment is linked, not copied (one file, no drift)"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2b: a fragment carrying substitutions is still GENERATED (AC2).
#
# A symlink cannot turn {{WORKING_BRANCH}} into "develop". The two kinds of
# fragment are not a style choice — parameterised ones are genuinely different
# per repo and must keep being written out.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": { "WORKING_BRANCH": "develop", "PRODUCTION_BRANCH": "main" } }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
if [ -L "$ws/repo/.claude/rules/00-universal.md" ]; then
  no "parameterised fragment is generated" "it was linked — {{VARS}} would reach the repo unsubstituted"
elif ! grep -q "Work on develop, ship to main." "$ws/repo/CLAUDE.md"; then
  no "parameterised fragment is generated" "substituted text missing: $(cat "$ws/repo/CLAUDE.md")"
else ok "a fragment with substitutions is still generated"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2c: the link is relative, so it survives the tree moving (AC5).
#
# An absolute link bakes /home/patrick into a committed file and breaks the
# moment the same repo is checked out on the Mac. Relative keeps working as
# long as claude-env stays a sibling — which is a real constraint, and is
# recorded on CE-5.1 rather than hidden here.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["stack-windows-service"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
target=$(readlink "$ws/repo/.claude/rules/stack-windows-service.md")
case "$target" in
  /*) no "the link is relative" "absolute target bakes in a machine path: $target" ;;
  *)  mv "$ws" "$ws-moved"
      if [ -r "$ws-moved/repo/.claude/rules/stack-windows-service.md" ]; then
        ok "the link is relative and survives the tree moving"
      else no "the link is relative" "broke when the workspace moved: $target"; fi
      ws="$ws-moved" ;;
esac
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2d: --check reports a BROKEN link loudly (AC4).
#
# Absence replaces drift as the way inheritance fails, and it is the quieter
# failure of the two: a repo with a dangling link inherits nothing while
# looking exactly like a healthy one. If --check cannot see this, the whole
# mechanism is worse than what it replaced.
ws=$(make_workspace)
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["stack-windows-service"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
link="$ws/repo/.claude/rules/stack-windows-service.md"
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" >/dev/null 2>&1; rc_ok=$?
rm "$link"; ln -s /nonexistent/gone.md "$link"
out_broken=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" 2>&1); rc_broken=$?
rm "$link"
out_gone=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" 2>&1); rc_gone=$?
if [ "$rc_ok" -ne 0 ]; then no "--check catches a broken link" "healthy repo already failed: rc=$rc_ok"
elif [ "$rc_broken" -eq 0 ]; then no "--check catches a broken link" "dangling link passed --check"
elif [ "$rc_gone" -eq 0 ]; then no "--check catches a broken link" "missing link passed --check"
elif ! echo "$out_broken$out_gone" | grep -q "stack-windows-service"; then
  no "--check catches a broken link" "failed without naming the fragment: $out_broken / $out_gone"
else ok "--check refuses a broken or missing link, and names it"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2e: a link pointing at the WRONG fragment is caught (AC5).
#
# Existing and resolving is not the same as being right. A link that resolves
# to readable content passes every existence check while delivering rules the
# repo never asked for.
ws=$(make_workspace)
printf '## Other
Different rules entirely.
' > "$ws/env/shared/claude-md/stack-other.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["stack-windows-service"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
link="$ws/repo/.claude/rules/stack-windows-service.md"
rm "$link"; ln -s ../../../env/shared/claude-md/stack-other.md "$link"
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then no "--check catches a misdirected link" "link to the wrong fragment passed"
else ok "--check refuses a link pointing at the wrong fragment"; fi
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
