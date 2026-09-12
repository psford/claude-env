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
# Absolute before the cd below, or a relative path handed in by a human running
# the driver directly resolves against the scratch repo and silently sources
# nothing -- which then looks like the hook misbehaving.
fixture="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
hook="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
expect="$3"

setup() { :; }
TOOL_NAME="Bash"
COMMAND=""
FILE_PATH=""
CONTENT=""
TOOL_RESPONSE_JSON=""
EXPECT_MATCH=""
ENV_VARS=()

repo=$(mktemp -d)
# Invoked from here, not from the scratch repo -- see the same note in
# _exitcode_driver.sh. Process cwd and payload cwd being identical in every
# fixture is what made a whole defect class untestable (Grace, finding 5).
elsewhere=$(mktemp -d)
trap 'rm -rf "$repo" "$elsewhere"' EXIT
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

# BOTH streams. Discarding stderr made this driver report ac_staleness_guard as
# silent when it was speaking -- it writes plain text to stderr rather than the
# hookSpecificOutput JSON the others use. A driver that only listens on one
# channel produces exactly the false "it does nothing" this suite exists to
# prevent, and it produced one.
if [ "${#ENV_VARS[@]}" -gt 0 ]; then
  out=$(cd "$elsewhere" && printf '%s' "$payload" | env "${ENV_VARS[@]}" python3 "$hook" 2>&1)
else
  out=$(cd "$elsewhere" && printf '%s' "$payload" | python3 "$hook" 2>&1)
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
    out = data.get("hookSpecificOutput") or {}
    # A hook that exits 0 can still REFUSE, by answering permissionDecision
    # "deny" with a reason instead of additionalContext. Reading only
    # additionalContext made every such refusal look like silence -- which is
    # the exact observation this file's header says must never be ambiguous.
    # deploy_guard's hard block on workflow dispatches was untestable for that
    # reason, and shipped with no fixtures at all (CE-2.19, 2026-09-11).
    spoken = out.get("additionalContext") or ""
    if not spoken and out.get("permissionDecision") == "deny":
        spoken = out.get("reason") or "denied"
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
