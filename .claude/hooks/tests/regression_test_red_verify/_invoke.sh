#!/usr/bin/env bash
# Driver for regression_test_red_verify.py tests.
#
# This is a pre-push hook that:
#  1) reads pre-push lines (<local_ref> <local_sha> <remote_ref> <remote_sha>) on stdin
#  2) walks commits in the push range
#  3) for test-only commits, parses `RED: <sha>` from the message,
#     creates a worktree at <sha>, copies the test file in, runs vitest,
#     and demands a non-zero exit (proving the test catches the regression).
#
# We avoid needing a real vitest install by shimming `npx` on PATH: the shim
# returns exit code based on a FAIL_HERE marker in the test file contents.
#
# Each fixture is a bash file that declares:
#   setup_repo()             # builds the commit graph in the scratch repo
#   PRE_PUSH_REMOTE=<sha>    # optional override for the "remote" sha
#                            # (default: HEAD~1, or zeros for single-commit)
#
# Driver exit code:
#   0 → outcome matched the expectation (PASS → hook rc 0, BLOCK → hook rc 1)
#   1 → mismatch
set -uo pipefail
fixture="$1"
hook="$2"
expect="$3"

ZERO_SHA="0000000000000000000000000000000000000000"

shim_dir=$(mktemp -d)
scratch=$(mktemp -d)
trap 'rm -rf "$shim_dir" "$scratch"' EXIT

# `npx` shim. Recognizes `npx vitest run [flags] <files...>`.
# Exits 1 (test fails) if any file contains FAIL_HERE; else 0 (test passes,
# meaning the test does NOT catch the bug — RED verification should fail).
cat > "$shim_dir/npx" <<'SHIM'
#!/usr/bin/env bash
if [ "${1:-}" != "vitest" ]; then exit 0; fi
shift
[ "${1:-}" = "run" ] && shift
while [ $# -gt 0 ]; do
  case "$1" in
    --*) shift ;;
    *) break ;;
  esac
done
for f in "$@"; do
  if [ -f "$f" ] && grep -q 'FAIL_HERE' "$f"; then
    echo "(shim) FAIL: $f"
    exit 1
  fi
done
echo "(shim) PASS (no FAIL_HERE marker)"
exit 0
SHIM
chmod +x "$shim_dir/npx"

# Fixture defaults.
setup_repo() { :; }
PRE_PUSH_REMOTE=""

# shellcheck disable=SC1090
source "$fixture"

cd "$scratch" || exit 1
git init -q -b main
git config user.email test@example.com
git config user.name test
git config commit.gpgsign false

setup_repo

head_sha=$(git rev-parse HEAD 2>/dev/null || true)
if [ -z "$head_sha" ]; then
  echo "setup_repo did not produce any commits"
  exit 1
fi

if [ -n "$PRE_PUSH_REMOTE" ]; then
  remote_sha="$PRE_PUSH_REMOTE"
elif git rev-parse 'HEAD~1' >/dev/null 2>&1; then
  remote_sha=$(git rev-parse 'HEAD~1')
else
  remote_sha="$ZERO_SHA"
fi

input=$(printf 'refs/heads/main %s refs/heads/main %s\n' "$head_sha" "$remote_sha")

out=$(echo "$input" | PATH="$shim_dir:$PATH" python3 "$hook" 2>&1)
rc=$?

case "$expect" in
  PASS)
    if [ "$rc" -eq 0 ]; then exit 0; fi
    echo "expected PASS (hook rc 0) but hook exited $rc"
    echo "--- hook output ---"
    echo "$out"
    exit 1
    ;;
  BLOCK)
    if [ "$rc" -eq 1 ]; then exit 0; fi
    echo "expected BLOCK (hook rc 1) but hook exited $rc"
    echo "--- hook output ---"
    echo "$out"
    exit 1
    ;;
  *)
    echo "unknown expectation: $expect"
    exit 1
    ;;
esac
