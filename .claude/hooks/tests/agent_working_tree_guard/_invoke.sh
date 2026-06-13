#!/usr/bin/env bash
# Driver for agent_working_tree_guard.py tests.
#
# Each fixture is a bash file that declares the scenario via these vars/fns:
#   BASELINE_FILES=(path ...)      # committed before snapshot+mutation
#   pre_dirty()                    # optional: mutations DIRTYING tree before snapshot
#   SKIP_SNAPSHOT=0|1              # if 1, skip running the Pre snapshot hook
#                                  #   (simulates "snapshot missing" fallback)
#   agent_mutations()              # the mutations the simulated subagent makes
#   EXPECT=silent|<substring>      # "silent" → guard stdout must be empty
#                                  # otherwise → stdout must contain substring
#   EXPECT_NOT=<substring>         # optional: stdout must NOT contain substring
#
# Each test runs in a fresh scratch git repo. We invoke the matched Pre/Post
# pair (agent_working_tree_snapshot.py + agent_working_tree_guard.py).
#
# Driver exit code:
#   0 → observed behavior matched
#   1 → mismatch
set -uo pipefail
fixture="$1"
hook="$2"     # this is the Post hook, agent_working_tree_guard.py
expect_outcome="$3"

# Resolve sibling hooks. Snapshot is the Pre half of the pair.
hooks_dir="$(dirname "$hook")"
snapshot_hook="$hooks_dir/agent_working_tree_snapshot.py"

if [ ! -f "$snapshot_hook" ]; then
  echo "missing pair hook: $snapshot_hook"
  exit 1
fi

# Reset defaults; the fixture may override.
BASELINE_FILES=()
SKIP_SNAPSHOT=0
EXPECT="silent"
EXPECT_NOT=""
pre_dirty() { :; }
agent_mutations() { :; }

# shellcheck disable=SC1090
source "$fixture"

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

cd "$scratch" || exit 1
git init -q
git config user.email test@example.com
git config user.name test

# Seed baseline and commit so the baseline isn't dirty.
for f in "${BASELINE_FILES[@]}"; do
  mkdir -p "$(dirname "$f")"
  printf 'baseline\n' > "$f"
done
if [ "${#BASELINE_FILES[@]}" -gt 0 ]; then
  git add . >/dev/null
  git commit -q -m baseline
fi

pre_dirty

# Synthetic tool_input — same hash on Pre and Post → snapshot path matches.
tool_input='{"subagent_type":"general-purpose","description":"x","prompt":"y"}'
session_id="hooktest-$$"
payload=$(printf '{"tool_name":"Agent","session_id":"%s","tool_input":%s}' "$session_id" "$tool_input")

if [ "$SKIP_SNAPSHOT" -eq 0 ]; then
  echo "$payload" | python3 "$snapshot_hook" >/dev/null 2>&1
fi

agent_mutations

out=$(echo "$payload" | python3 "$hook" 2>&1)
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "guard hook exited non-zero ($rc) — should always be 0"
  echo "$out"
  exit 1
fi

# Sanity: outcome filename and EXPECT must be consistent.
# PASS  → expect silent guard output (no additionalContext)
# BLOCK → expect guard to fire with additionalContext containing EXPECT substring
case "$expect_outcome" in
  PASS)
    if [ "$EXPECT" != "silent" ]; then
      echo "fixture mismatch: filename says PASS but EXPECT=$EXPECT (not 'silent')"
      exit 1
    fi
    if [ -n "$out" ]; then
      echo "expected silent guard but stdout was:"
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
    if [ -z "$out" ]; then
      echo "expected guard to fire (substring '$EXPECT') but stdout was empty"
      exit 1
    fi
    if ! grep -qF "$EXPECT" <<<"$out"; then
      echo "expected substring '$EXPECT' not found in guard output:"
      echo "$out"
      exit 1
    fi
    if [ -n "$EXPECT_NOT" ] && grep -qF "$EXPECT_NOT" <<<"$out"; then
      echo "forbidden substring '$EXPECT_NOT' WAS found in guard output:"
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
