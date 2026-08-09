#!/usr/bin/env bash
# Shared driver for ADVISORY hooks — the ones that never block.
#
# Why this exists. The runner's vocabulary is PASS/BLOCK, which is exit 0 vs
# exit 2. Every hook activated by CH-47 is advisory: it always exits 0 and
# speaks by printing hookSpecificOutput.additionalContext. Under PASS/BLOCK a
# hook that fires correctly and a hook that does nothing at all are the same
# observation.
#
# That is not a hypothetical. CH-47's pre-flight ran all 13 against four payload
# shapes and reported "13 of 13 ran clean, zero non-zero exits" — which was true
# and proved only that they do not crash. Patrick returned the story with
# `iterate` because wired is not working, and he was right.
#
# So this driver judges what the hook SAID:
#
#   FIRES   the hook produced additionalContext, and it matches EXPECT_MATCH
#   SILENT  the hook produced no additionalContext at all
#
# EXPECT_MATCH is REQUIRED on a FIRES fixture. "Produced some output" is the
# weak assertion that let CH-55's queue command ship with the wrong --actor;
# a fixture has to say which message it expected.
#
# Fixture contract (a bash file, sourced):
#   setup()              optional: build repo state in $PWD
#   TOOL_NAME            default "Bash"
#   COMMAND              for Bash payloads
#   FILE_PATH, CONTENT   for Write/Edit payloads
#   TOOL_RESPONSE_JSON   optional raw JSON for PostToolUse hooks
#   ENV_VARS=(K=V ...)   optional
#   EXPECT_MATCH         extended regex the additionalContext must match (FIRES)
#
# Driver exit code: 0 iff the observation matched the expectation.
set -uo pipefail
fixture="$1"; hook="$2"; expect="$3"

setup() { :; }
TOOL_NAME="Bash"
COMMAND=""
FILE_PATH=""
CONTENT=""
TOOL_RESPONSE_JSON=""
EXPECT_MATCH=""
ENV_VARS=()

repo=$(mktemp -d)
trap 'rm -rf "$repo"' EXIT
(
  cd "$repo" && git init -q && git config user.email t@example.com && git config user.name t \
    && printf 'baseline\n' > README.md && git add README.md && git commit -q -m baseline
)

cd "$repo" || exit 1
# shellcheck disable=SC1090
source "$fixture"
setup

payload=$(TOOL_NAME="$TOOL_NAME" COMMAND="$COMMAND" FILE_PATH="$FILE_PATH" \
          CONTENT="$CONTENT" TOOL_RESPONSE_JSON="$TOOL_RESPONSE_JSON" REPO="$repo" \
          python3 - <<'PYEOF'
import json, os
tool = os.environ["TOOL_NAME"]
repo = os.environ["REPO"]
if tool == "Bash":
    tool_input = {"command": os.environ["COMMAND"]}
else:
    tool_input = {"file_path": os.environ["FILE_PATH"], "content": os.environ["CONTENT"]}
payload = {"tool_name": tool, "tool_input": tool_input, "cwd": repo}
raw = os.environ.get("TOOL_RESPONSE_JSON") or ""
if raw.strip():
    payload["tool_response"] = json.loads(raw)
print(json.dumps(payload))
PYEOF
)

if [ "${#ENV_VARS[@]}" -gt 0 ]; then
  out=$(printf '%s' "$payload" | env "${ENV_VARS[@]}" python3 "$hook" 2>/dev/null)
else
  out=$(printf '%s' "$payload" | python3 "$hook" 2>/dev/null)
fi
rc=$?

# An advisory hook must never block. A non-zero exit is a failure regardless of
# what the fixture expected -- that is the property the whole batch rests on.
if [ "$rc" -ne 0 ]; then
  echo "advisory hook exited $rc (must always be 0). output: $out"
  exit 1
fi

context=$(OUT="$out" python3 - <<'PYEOF'
import json, os
raw = (os.environ.get("OUT") or "").strip()
if not raw:
    raise SystemExit(0)
try:
    data = json.loads(raw)
except Exception:
    # Not JSON. Some hooks print plain advisory text; treat it as having spoken
    # rather than pretending silence -- a false SILENT would be the mask.
    print(raw)
    raise SystemExit(0)
if isinstance(data, dict):
    spoken = (data.get("hookSpecificOutput") or {}).get("additionalContext") or ""
    print(spoken.strip() or "")
PYEOF
)

case "$expect" in
  FIRES)
    if [ -z "$context" ]; then
      echo "expected the hook to speak, it said nothing"
      exit 1
    fi
    if [ -z "$EXPECT_MATCH" ]; then
      echo "fixture is FIRES but sets no EXPECT_MATCH — 'said something' is not a test"
      exit 1
    fi
    if ! printf '%s' "$context" | grep -Eqi -- "$EXPECT_MATCH"; then
      echo "context did not match /$EXPECT_MATCH/"
      printf '%s\n' "$context" | head -12
      exit 1
    fi
    exit 0
    ;;
  SILENT)
    if [ -n "$context" ]; then
      echo "expected silence, the hook spoke:"
      printf '%s\n' "$context" | head -12
      exit 1
    fi
    exit 0
    ;;
  *)
    echo "advisory driver understands FIRES and SILENT, got '$expect'"
    exit 1
    ;;
esac
