#!/usr/bin/env bash
# run.sh — canonical pre-merge verification for the polytoken layer:
#   1. unit tests (pytest if available, else unittest)
#   2. shellcheck on every shipped script (skip with a notice if absent)
#   3. history-wide secrets scan
# Run from anywhere: `bash polytoken/tests/run.sh`. Exit 0 = all green.
# This repo has no CI test runner; this script IS the pre-merge gate, and
# its result is stated in the PR body per repo convention.

set -u
cd "$(dirname "$0")/../.." || exit 1   # repo root
LAYER="polytoken"
STATUS=0

say() { printf '\n== %s ==\n' "$1"; }

# ------------------------------------------------------------ unit tests
say "unit tests ($LAYER/tests)"
if python3 -c 'import pytest' >/dev/null 2>&1; then
  python3 -m pytest "$LAYER/tests" -q || STATUS=1
else
  ( cd "$LAYER/tests" && python3 -m unittest discover -p 'test_*.py' ) || STATUS=1
fi

# ------------------------------------------------------------- shellcheck
say "shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
  RC=0
  for f in "$LAYER/bootstrap.sh" "$LAYER/hooks/todo-sync.sh" \
           "$LAYER/hooks/todo-restore.sh" "$LAYER/tests/acceptance.sh" \
           "$LAYER/tests/run.sh"; do
    shellcheck "$f" || RC=1
  done
  [ "$RC" = 0 ] || STATUS=1
else
  printf 'SKIP: shellcheck not installed (brew install shellcheck / apt install shellcheck)\n'
fi

# ------------------------------------------------------------ secrets scan
say "secrets scan (history-wide)"
# Patterns from the plan: tavily keys, OpenAI-style keys, and the ZAI key
# shape (32 hex, dot, 16 alnum). Judged by OUTPUT, not exit code: a clean
# git grep exits 1 and xargs propagates 123, but a history with BOTH hits
# and clean commits also yields 123 — so exit codes cannot distinguish
# clean from dirty. Output lines can.
if git rev-parse --git-dir >/dev/null 2>&1; then
  PATTERN='tvly-[A-Za-z0-9][A-Za-z0-9-]{19,}|sk-[A-Za-z0-9]{20,}|[0-9a-f]{32}\.[A-Za-z0-9]{16}'
  HITS="$(git rev-list --all 2>/dev/null \
    | xargs -I{} git grep -E "$PATTERN" {} -- 2>/dev/null)"
  if [ -n "$HITS" ]; then
    printf 'SECRETS SCAN FAILED — matches in history:\n%s\n' "$HITS"
    STATUS=1
  else
    printf 'secrets scan: clean (no matches in any commit)\n'
  fi
else
  printf 'SKIP: not a git repo (running from an exported copy?)\n'
fi

say "result"
if [ "$STATUS" = 0 ]; then
  printf 'ALL GREEN\n'
else
  printf 'FAILURES ABOVE\n'
fi
exit "$STATUS"
