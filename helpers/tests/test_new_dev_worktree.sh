#!/usr/bin/env bash
# Tests for helpers/new-dev-worktree.sh (CE-2.50) — the sanctioned way to
# create a dev worktree that comes out inheriting the shared rules.
#
# Same ad hoc style as test_sync_claude_md.sh: a plain script with its own
# pass/fail counters, no shared runner. Run directly:
#   bash helpers/tests/test_new_dev_worktree.sh
set -uo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SELF_DIR/../new-dev-worktree.sh"
SYNC="$SELF_DIR/../sync-claude-md.sh"

pass=0; fail=0
ok()  { echo "  ✓ $1"; pass=$((pass+1)); }
no()  { echo "  ✗ $1"; echo "     $2" | sed 's/^/     /'; fail=$((fail+1)); }

# A fake claude-env (fragments only — new-dev-worktree.sh finds sync-claude-md.sh
# via its OWN location, not via the fake env) + a real git repo playing the
# part of a companion repo, opted into the shared rules via claude-md.json.
make_git_repo() {
  local ws; ws=$(mktemp -d)
  mkdir -p "$ws/env/shared/claude-md" "$ws/repo/.claude"
  printf '## Shared\nInvariant rules.\n' > "$ws/env/shared/claude-md/00-universal.md"
  git init -q -b develop "$ws/repo"
  git -C "$ws/repo" config user.email t@example.com
  git -C "$ws/repo" config user.name t
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > "$ws/repo/.claude/claude-md.json"
  printf '# Repo\nLocal contracts.\n' > "$ws/repo/CLAUDE.local.md"
  git -C "$ws/repo" add -A
  git -C "$ws/repo" commit -q -m baseline
  echo "$ws"
}

echo "── new-dev-worktree.sh ──"

# ---------------------------------------------------------------------------
# Test 1 (AC1): the worktree the helper creates passes sync-claude-md.sh
# --check straight away — no separate sync step for the caller to remember.
ws=$(make_git_repo)
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" TEST-1 develop 2>&1); rc=$?
wt="$ws/repo--TEST-1"
if [ "$rc" -ne 0 ]; then no "helper creates an inheriting worktree" "exit $rc: $out"
elif [ ! -d "$wt" ]; then no "helper creates an inheriting worktree" "no worktree at $wt"
else
  branch=$(git -C "$wt" rev-parse --abbrev-ref HEAD)
  check_out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SYNC" --check "$wt" 2>&1); check_rc=$?
  if [ "$branch" != "dev/TEST-1" ]; then
    no "helper creates an inheriting worktree" "branch is $branch, not dev/TEST-1"
  elif [ "$check_rc" -ne 0 ]; then
    no "helper creates an inheriting worktree" "sync-claude-md.sh --check failed: $check_out"
  else ok "a worktree made by the helper passes --check immediately"; fi
fi
git -C "$ws/repo" worktree remove --force "$wt" >/dev/null 2>&1
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 2: refuses to clobber a worktree path that already exists.
ws=$(make_git_repo)
mkdir -p "$ws/repo--TEST-2"
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" "$ws/repo" TEST-2 develop 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then no "refuses an existing path" "exited 0 instead of refusing"
elif ! echo "$out" | grep -q "already exists"; then
  no "refuses an existing path" "did not name the problem: $out"
else ok "refuses to create a worktree where one already exists"; fi
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 3: a repo not opted into the shared rules (no claude-md.json) still
# gets its worktree — the helper must not block ordinary git work over a
# feature this repo never asked for.
ws=$(mktemp -d)
git init -q -b develop "$ws/repo"
git -C "$ws/repo" config user.email t@example.com
git -C "$ws/repo" config user.name t
printf 'hello\n' > "$ws/repo/README.md"
git -C "$ws/repo" add -A
git -C "$ws/repo" commit -q -m baseline
out=$(CLAUDE_ENV_ROOT="$ws/env-does-not-exist" bash "$SCRIPT" "$ws/repo" TEST-3 develop 2>&1); rc=$?
wt="$ws/repo--TEST-3"
if [ "$rc" -ne 0 ]; then no "repo not opted in still gets a worktree" "exit $rc: $out"
elif [ ! -d "$wt" ]; then no "repo not opted in still gets a worktree" "no worktree at $wt"
else ok "a repo with no claude-md.json still gets its worktree, sync skipped"; fi
git -C "$ws/repo" worktree remove --force "$wt" >/dev/null 2>&1
rm -rf "$ws"

# ---------------------------------------------------------------------------
# Test 4 (AC2, via the helper's own --check mode): pointed at a worktree
# made by a BARE `git worktree add` (no sync step at all), it reports the
# problem — non-zero, naming the fragment — before any work happens in it.
ws=$(make_git_repo)
wt="$ws/repo--TEST-4"
git -C "$ws/repo" worktree add -q -b dev/TEST-4 "$wt" develop
out=$(CLAUDE_ENV_ROOT="$ws/env" bash "$SCRIPT" --check "$wt" 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then no "--check catches a bare worktree add" "exited 0 on an unlinked worktree"
elif ! echo "$out" | grep -q "00-universal"; then
  no "--check catches a bare worktree add" "did not name the fragment: $out"
else ok "--check mode reports a bare-worktree-add worktree before any work happens, naming the fragment"; fi
git -C "$ws/repo" worktree remove --force "$wt" >/dev/null 2>&1
rm -rf "$ws"

echo ""
if [ "$fail" -eq 0 ]; then echo "ALL $pass NEW-DEV-WORKTREE TESTS PASSED"; exit 0
else echo "$fail of $((pass+fail)) NEW-DEV-WORKTREE TESTS FAILED"; exit 1
fi
