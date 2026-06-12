#!/usr/bin/env bash
# Hook test runner. Patrick should be able to run this any time and see
# green/red across every hook in this directory — without having to trust
# that any single hook was tested when it shipped.
#
# Convention: tests live in .claude/hooks/tests/<hook_name>/<NN>-<desc>.<EXPECT>.md
# where <EXPECT> is PASS or BLOCK. The runner stages each fixture into a
# scratch git repo, pipes a synthetic "git commit" Bash input through the
# hook, and asserts the exit code matches the expectation (0 for PASS,
# 2 for BLOCK).
#
# Usage:
#   bash .claude/hooks/tests/run-hook-tests.sh
#   bash .claude/hooks/tests/run-hook-tests.sh defer_forever_guard
#
# Exit code: 0 if all tests pass, 1 if any fails.

set -uo pipefail
# Script lives at <repo>/.claude/hooks/tests/run-hook-tests.sh.
# HOOKS_DIR is one level up; TESTS_DIR is this directory.
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTS_DIR="$SELF_DIR"
HOOKS_DIR="$(cd "$SELF_DIR/.." && pwd)"
FILTER="${1:-}"

red()    { printf "\033[31m%s\033[0m" "$1"; }
green()  { printf "\033[32m%s\033[0m" "$1"; }
yellow() { printf "\033[33m%s\033[0m" "$1"; }

REPO=$(mktemp -d)
trap 'rm -rf "$REPO"' EXIT
( cd "$REPO" && git init -q )

pass=0
fail=0
total=0

for hook_dir in "$TESTS_DIR"/*/; do
  hook_name="$(basename "$hook_dir")"
  [ -n "$FILTER" ] && [ "$FILTER" != "$hook_name" ] && continue
  hook_script="$HOOKS_DIR/$hook_name.py"
  [ -f "$hook_script" ] || { echo "$(yellow "[skip]") $hook_name (no $hook_script)"; continue; }

  echo ""
  echo "── $(yellow "$hook_name") ──"

  for fixture in "$hook_dir"/*.md; do
    [ -e "$fixture" ] || continue
    base="$(basename "$fixture")"
    # filename convention: NN-name.EXPECT.md  →  EXPECT ∈ {PASS, BLOCK}
    expect="$(echo "$base" | sed -E 's/^[0-9]+-.+\.(PASS|BLOCK)\.md$/\1/')"
    if [ "$expect" != "PASS" ] && [ "$expect" != "BLOCK" ]; then
      echo "  $(yellow "[skip]") $base — filename doesn't encode .PASS.md or .BLOCK.md"
      continue
    fi
    total=$((total + 1))

    cp "$fixture" "$REPO/case.md"
    ( cd "$REPO" && git add case.md >/dev/null 2>&1 )

    out=$(cd "$REPO" && echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' \
          | python3 "$hook_script" 2>&1)
    rc=$?
    ( cd "$REPO" && git rm -f case.md >/dev/null 2>&1 )

    expected_rc=0
    [ "$expect" = "BLOCK" ] && expected_rc=2

    if [ "$rc" -eq "$expected_rc" ]; then
      echo "  $(green "✓") $base (rc=$rc, expected $expected_rc)"
      pass=$((pass + 1))
    else
      echo "  $(red "✗") $base (rc=$rc, expected $expected_rc)"
      echo "$out" | sed 's/^/      /' | head -8
      fail=$((fail + 1))
    fi
  done
done

echo ""
if [ "$fail" -eq 0 ] && [ "$total" -gt 0 ]; then
  echo "$(green "ALL $total HOOK TESTS PASSED")"
  exit 0
elif [ "$total" -eq 0 ]; then
  echo "$(yellow "NO HOOK TESTS FOUND")"
  exit 0
else
  echo "$(red "$fail of $total HOOK TESTS FAILED")"
  exit 1
fi
