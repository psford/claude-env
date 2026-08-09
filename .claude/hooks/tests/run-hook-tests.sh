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
# Per-hook drivers: if <hook_name>/_invoke.sh exists, the runner delegates
# to it instead of the default synthetic-Bash-payload path. The driver gets:
#   $1 = absolute path to fixture file
#   $2 = absolute path to hook script ($HOOKS_DIR/<hook_name>.py)
#   $3 = expected outcome (PASS or BLOCK)
# The driver is responsible for setting up its own scratch state and
# producing an exit code that maps to the expected outcome: rc 0 means
# "matched the expectation," rc != 0 means "did not match." The driver
# should write any diagnostic output to stdout/stderr.
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

  invoke_script="$hook_dir/_invoke.sh"
  has_driver=0
  [ -x "$invoke_script" ] && has_driver=1

  # Skip non-fixture files (._invoke.sh, fixtures.d/, etc.) by globbing only *.md.
  for fixture in "$hook_dir"/*.md; do
    [ -e "$fixture" ] || continue
    base="$(basename "$fixture")"
    # filename convention: NN-name.EXPECT.md
    #   PASS / BLOCK    exit code 0 / 2 — for hooks that can refuse
    #   FIRES / SILENT  did the hook SPEAK — for advisory hooks, which always
    #                   exit 0 and are therefore indistinguishable under
    #                   PASS/BLOCK. CH-47 activated 13 of them on the strength
    #                   of "13 of 13 ran clean", which proved only that they do
    #                   not crash. These two need a driver: an exit code cannot
    #                   answer the question.
    expect="$(echo "$base" | sed -E 's/^[0-9]+-.+\.(PASS|BLOCK|FIRES|SILENT)\.md$/\1/')"
    case "$expect" in
      PASS|BLOCK|FIRES|SILENT) ;;
      *)
        # Counted and FAILED, not skipped. A fixture whose name does not parse
        # used to vanish from the run in yellow -- a typo silently reducing
        # coverage, which is the same "skipping X" mask this repo keeps finding.
        echo "  $(red "✗") $base — filename encodes no known expectation"
        total=$((total + 1)); fail=$((fail + 1))
        continue
        ;;
    esac
    if { [ "$expect" = "FIRES" ] || [ "$expect" = "SILENT" ]; } && [ "$has_driver" -eq 0 ]; then
      echo "  $(red "✗") $base — $expect needs a driver; an exit code cannot judge it"
      total=$((total + 1)); fail=$((fail + 1))
      continue
    fi
    total=$((total + 1))

    if [ "$has_driver" -eq 1 ]; then
      # Delegate to the per-hook driver. Driver returns rc 0 iff it
      # observed the expected outcome.
      out=$( "$invoke_script" "$fixture" "$hook_script" "$expect" 2>&1 )
      rc=$?
      if [ "$rc" -eq 0 ]; then
        echo "  $(green "✓") $base ($expect via _invoke.sh)"
        pass=$((pass + 1))
      else
        echo "  $(red "✗") $base ($expect via _invoke.sh, driver rc=$rc)"
        echo "$out" | sed 's/^/      /' | head -20
        fail=$((fail + 1))
      fi
      continue
    fi

    # Default path: synthetic `git commit` Bash payload through the hook.
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
  green "ALL $total HOOK TESTS PASSED"; echo
  exit 0
elif [ "$total" -eq 0 ]; then
  yellow "NO HOOK TESTS FOUND"; echo
  exit 0
else
  red "$fail of $total HOOK TESTS FAILED"; echo
  exit 1
fi
