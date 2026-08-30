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

# ---------------------------------------------------------------------------
# Test 6: the repo IS the env root — claude-env linking its own fragments.
#
# CE-5.2. Every test above builds env/ and repo/ as siblings, so the link is
# ../../../env/... . claude-env is not a sibling of itself: its link is
# ../../shared/claude-md/x.md and never leaves the repo. Nothing had exercised
# that, and a script that hard-coded the sibling shape would emit a path
# pointing at a directory named claude-env NEXT TO claude-env.
#
# The assertion is on the target STRING, not on the link resolving. A
# wrong-but-lucky path can resolve on a machine that happens to have a sibling
# checkout, which is exactly the machine this runs on.
ws=$(mktemp -d)
mkdir -p "$ws/self/shared/claude-md" "$ws/self/.claude"
printf '## Shared
Rules that live here.
' > "$ws/self/shared/claude-md/00-universal.md"
printf '# Self
Local contracts.
' > "$ws/self/CLAUDE.local.md"
cat > "$ws/self/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/self" bash "$SCRIPT" "$ws/self" >/dev/null 2>&1
target=$(readlink "$ws/self/.claude/rules/00-universal.md" 2>/dev/null)
if [ -z "$target" ]; then no "a repo can link its own fragments" "no link written"
elif [ "$target" != "../../shared/claude-md/00-universal.md" ]; then
  no "a repo can link its own fragments" "target escapes the repo: $target"
elif [ "$(cat "$ws/self/.claude/rules/00-universal.md")" != "$(cat "$ws/self/shared/claude-md/00-universal.md")" ]; then
  no "a repo can link its own fragments" "link does not read back the source"
else ok "a repo that owns the fragments links to them without leaving itself"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 7: one linked and one generated fragment in the same repo (CE-5.2).
#
# Both harness repos take 00-universal (linkable) and git-flow (generated).
# Asserted together on purpose: the link alone passes under a script that links
# everything, and the substitution alone passes under one that links nothing.
# Only the pair distinguishes a correct split from either failure.
ws=$(make_workspace)
printf '## Flow
Work on %s.
' '{{WORKING_BRANCH}}' > "$ws/env/shared/claude-md/git-flow.md"
printf '## Shared
Invariant rules.
' > "$ws/env/shared/claude-md/00-universal.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal", "git-flow"], "vars": { "WORKING_BRANCH": "develop" } }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
gen="$ws/repo/CLAUDE.md"
if [ ! -L "$ws/repo/.claude/rules/00-universal.md" ]; then
  no "mixed linked + generated" "the var-free fragment was not linked"
elif [ -L "$ws/repo/.claude/rules/git-flow.md" ]; then
  no "mixed linked + generated" "the parameterised fragment was linked — {{VARS}} would reach the repo raw"
elif ! grep -q "Work on develop\." "$gen"; then
  no "mixed linked + generated" "branch name not substituted: $(cat "$gen")"
elif grep -q "Invariant rules\." "$gen"; then
  no "mixed linked + generated" "the linked fragment's text is ALSO in CLAUDE.md"
elif grep -q "{{" "$gen"; then no "mixed linked + generated" "an unsubstituted token survived"
else ok "one repo holds a link and a generated fragment, each doing its own job"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 8: converting a repo REPLACES an existing regular file (CE-5.2).
#
# The prior state of all nine repos is a copy, so conversion is not creation.
# A script that skips a path already occupied would leave every one of them
# exactly as it found them, and every existence check would still pass.
ws=$(make_workspace)
printf '## Shared
Invariant rules.
' > "$ws/env/shared/claude-md/00-universal.md"
mkdir -p "$ws/repo/.claude/rules"
printf 'a stale copy from before the conversion
' > "$ws/repo/.claude/rules/00-universal.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
dest="$ws/repo/.claude/rules/00-universal.md"
if [ ! -L "$dest" ]; then no "conversion replaces a copy" "still a regular file"
elif grep -q "stale copy" "$dest"; then no "conversion replaces a copy" "old content survived"
else ok "conversion replaces an existing copy with a link"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 9: --check refuses a repo that has NOT been converted yet (CE-5.2).
#
# This is what makes --check able to drive the rollout rather than merely
# confirm it afterwards. A repo still holding copies must be reported, not
# passed over because its CLAUDE.md happens to match what it used to generate.
ws=$(make_workspace)
printf '## Shared
Invariant rules.
' > "$ws/env/shared/claude-md/00-universal.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": {} }
JSON
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then no "--check refuses an unconverted repo" "exited 0 with no link present"
elif ! echo "$out" | grep -q "00-universal"; then
  no "--check refuses an unconverted repo" "failed without naming the fragment: $out"
else ok "--check refuses a repo that still holds copies, and names it"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 10: running twice changes nothing (CE-5.2).
#
# A script that unlinks and recreates on every run dirties git status in nine
# repos for no reason, and makes --check's answer depend on when it last ran.
ws=$(make_workspace)
printf '## Shared
Invariant rules.
' > "$ws/env/shared/claude-md/00-universal.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
before_link=$(readlink "$ws/repo/.claude/rules/00-universal.md")
before_md=$(cat "$ws/repo/CLAUDE.md")
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" >/dev/null 2>&1
if [ "$(readlink "$ws/repo/.claude/rules/00-universal.md")" != "$before_link" ]; then
  no "the second run is a no-op" "link target changed"
elif [ "$(cat "$ws/repo/CLAUDE.md")" != "$before_md" ]; then
  no "the second run is a no-op" "CLAUDE.md changed on an unchanged input"
else ok "running the script twice changes nothing"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 11: --check creates nothing, not even the directory it inspects.
#
# Found by a control that could not fail: the mutation being tested skipped
# repos with no .claude/rules, and --check had already CREATED that directory
# before reaching the check. The instrument was building the thing it was
# looking for. Test 5 only asserted CLAUDE.md was untouched, which is the
# narrower half of read-only.
ws=$(make_workspace)
printf '## Shared\nInvariant rules.\n' > "$ws/env/shared/claude-md/00-universal.md"
cat > "$ws/repo/.claude/claude-md.json" <<'JSON'
{ "fragments": ["00-universal"], "vars": {} }
JSON
CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$ws/repo" >/dev/null 2>&1
if [ -d "$ws/repo/.claude/rules" ]; then
  no "--check creates nothing" ".claude/rules was created by a read-only check"
elif [ -f "$ws/repo/CLAUDE.md" ]; then
  no "--check creates nothing" "CLAUDE.md was written by a read-only check"
else ok "--check creates nothing, not even the directory it inspects"; fi
rm -rf "$ws"

echo ""
if [ "$fail" -eq 0 ]; then echo "ALL $pass SYNC TESTS PASSED"; exit 0
else echo "$fail of $((pass+fail)) SYNC TESTS FAILED"; exit 1; fi
