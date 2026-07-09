#!/usr/bin/env bash
# Driver for plan_staleness_scan.py tests.
#
# plan_staleness_scan.py is a SessionStart hook: it reads no stdin, and
# scans docs/decisions.md + docs/implementation-plans/**/*.md ON DISK
# (relative to cwd) rather than staged/git state. It always exits 0
# (advisory only) — the assertion is on stdout content, not rc.
#
# Each fixture is a bash file sourced by this driver. It declares:
#   setup()          # required: write docs/decisions.md + plan file(s) into $PWD
#   EXPECT=silent|<substring>   # "silent" -> stdout must be empty
#                                # otherwise -> stdout must contain substring
#
# Driver exit code: 0 -> observed output matched EXPECT (and rc was 0).
set -uo pipefail
fixture="$1"; hook="$2"; expect_outcome="$3"

setup() { :; }
EXPECT="silent"

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch" || exit 1

# shellcheck disable=SC1090
source "$fixture"
setup

out=$(python3 "$hook" 2>&1)
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "hook exited non-zero ($rc) — should always be 0 (advisory)"
  echo "$out"
  exit 1
fi

case "$expect_outcome" in
  PASS)
    if [ "$EXPECT" != "silent" ]; then
      echo "fixture mismatch: filename says PASS but EXPECT=$EXPECT (not 'silent')"
      exit 1
    fi
    if [ -n "$out" ]; then
      echo "expected silent output but stdout was:"
      echo "$out"
      exit 1
    fi
    exit 0
    ;;
  BLOCK)
    if [ "$EXPECT" = "silent" ]; then
      echo "fixture mismatch: filename says BLOCK but EXPECT=silent"
      exit 1
    fi
    if ! grep -qF "$EXPECT" <<<"$out"; then
      echo "expected substring '$EXPECT' not found in output:"
      echo "$out"
      exit 1
    fi
    exit 0
    ;;
  *)
    echo "unknown expectation: $expect_outcome"
    exit 1
    ;;
esac
