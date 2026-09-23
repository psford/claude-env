#!/usr/bin/env python3
"""Stop hook: a decision that is Patrick's goes on the board, not in chat.

CE-2.55. Patrick, 2026-09-21: "I want you to figure out a way to use jev so
you stop ignoring memories we've been over dozens of times." The memory
broken most often, while held, was feedback_ask_on_the_board_and_wait: asking
him to approve something that is his by rule -- removing a criterion, new
test infrastructure, reopening a ticket -- in chat, instead of `ticket ask`
and a stop.

This file is thin on purpose. The question, its threshold and the
measurement behind them live in helpers/data/reply_rule_checks.json; the
logic lives in helpers/reply_rule_check.py.

CE-2.56, after the CSO review. Three outcomes, never a silent fourth:
  fired      -- block, and quote the rule.
  clean      -- exit 0, say nothing.
  unchecked  -- do NOT block (a broken classifier must never stop every
                reply), but exit 1 with the reason on stderr. Claude Code
                treats that as a non-blocking error and shows a
                "hook error" notice in the session, so a guard that is
                broken, or was switched off, is visible every time it
                fails to run instead of indistinguishable from a pass.

CE-2.62, after the third CSO review. The checks file is pinned: this hook
carries the SHA-256 of the measured file, and any other contents -- a swapped
question, an impossible threshold, an emptied list -- are unchecked, not
trusted. The file needs no approval to edit; this constant does. When the
question is re-measured, the new file's hash replaces this one in the same
change.

CE-2.63, after the fourth. Every message of the turn is checked, not just the
last: an ask made early in a multi-step turn used to go out unchecked. After
a Stop hook has blocked once in a turn, Claude Code sets stop_hook_active,
and every message written since the recorded block is checked: a rewrite
split across a tool call is checked in full, and the reply it replaced is
never refused again. And the bytes checked against the pin are the bytes
parsed: the file is read once.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "helpers"))

import reply_rule_check  # noqa: E402

CHECKS_SHA256 = "9d9b439dce5a758879c2f7d3d1b6fb6b585ec85975d4c91848a4003d9d2d79a6"


def unchecked(reason):
    print(f"reply_rule_guard: reply NOT checked -- {reason}", file=sys.stderr)
    return 1


def main(checks_path=None):
    checks_path = Path(checks_path or reply_rule_check.CHECKS_PATH)
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return unchecked("hook input was not JSON")
    path = data.get("transcript_path")
    if not path:
        return unchecked("no transcript_path in hook input")
    try:
        checks_bytes = checks_path.read_bytes()
    except OSError as e:
        return unchecked(f"checks file unreadable: {e.strerror}")
    actual = hashlib.sha256(checks_bytes).hexdigest()
    if actual != CHECKS_SHA256:
        return unchecked(f"checks file {checks_path.name} does not match the "
                         f"measured version pinned in this hook "
                         f"(sha256 {actual[:12]}, pinned {CHECKS_SHA256[:12]})")
    try:
        texts = reply_rule_check.turn_texts(
            path, since_block=bool(data.get("stop_hook_active")))
    except reply_rule_check.BlockNotFound as e:
        return unchecked(str(e))
    except OSError as e:
        return unchecked(f"transcript unreadable: {e.strerror}")
    except UnicodeDecodeError:
        return unchecked("transcript is not valid UTF-8 text")
    if not any(t.strip() for t in texts):
        return unchecked("no reply text found in the transcript")
    result = reply_rule_check.check_turn(texts, checks_path=checks_path,
                                         checks_bytes=checks_bytes)
    if result["status"] == "fired":
        print(json.dumps({"decision": "block",
                          "reason": reply_rule_check.block_reason(result["fired"])}))
        return 0
    if result["status"] == "unchecked":
        return unchecked(result["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
