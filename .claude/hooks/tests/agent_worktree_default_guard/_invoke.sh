#!/usr/bin/env bash
# Driver for agent_worktree_default_guard.py tests.
#
# Semantics:
#   PASS  → hook produces no JSON override (silent stdout). Either the
#           dispatch already pinned `isolation`, or the subagent_type is
#           in the read-only allowlist.
#   BLOCK → hook injects `updatedInput.isolation = "worktree"`, forcing
#           the safe default. Stdout is non-empty JSON containing
#           "isolation": "worktree".
#
# The hook ALWAYS exits 0 (a failure to check should never block dispatch).
# So we drive PASS/BLOCK off stdout content, not exit code.
#
# Driver exit code:
#   0 → observed behavior matched the expected outcome
#   1 → mismatch
set -uo pipefail
fixture="$1"
hook="$2"
expect="$3"

out=$(python3 "$hook" < "$fixture" 2>&1)
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "hook exited non-zero ($rc) — should always be 0"
  echo "stdout/stderr:"
  echo "$out"
  exit 1
fi

case "$expect" in
  PASS)
    if [ -z "$out" ]; then
      exit 0
    fi
    # Tolerate output that doesn't force worktree (e.g. some other
    # additionalContext), but `isolation: worktree` MUST not be present.
    if echo "$out" | grep -q '"isolation"[[:space:]]*:[[:space:]]*"worktree"'; then
      echo "expected PASS (hook should not force worktree) but got:"
      echo "$out"
      exit 1
    fi
    exit 0
    ;;
  BLOCK)
    if [ -z "$out" ]; then
      echo "expected BLOCK (hook should force worktree) but stdout was empty"
      exit 1
    fi
    if echo "$out" | grep -q '"isolation"[[:space:]]*:[[:space:]]*"worktree"'; then
      exit 0
    fi
    echo "expected BLOCK (hook should force worktree) but stdout was:"
    echo "$out"
    exit 1
    ;;
  *)
    echo "unknown expectation: $expect"
    exit 1
    ;;
esac
