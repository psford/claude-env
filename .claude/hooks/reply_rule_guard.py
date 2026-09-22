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
logic lives in helpers/reply_rule_check.py. The last reply is read by the
same function verification_claim_guard uses, imported rather than copied.

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
trusted. The file lives outside .claude/hooks/ and needs no approval to edit;
this constant does. So changing what the check asks now takes Patrick's
approval, the same as changing the hook. When the question is re-measured,
the new file's hash replaces this one in the same change.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "helpers"))

from verification_claim_guard import last_assistant_text  # noqa: E402
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
        actual = hashlib.sha256(checks_path.read_bytes()).hexdigest()
    except OSError as e:
        return unchecked(f"checks file unreadable: {e.strerror}")
    if actual != CHECKS_SHA256:
        return unchecked(f"checks file {checks_path.name} does not match the "
                         f"measured version pinned in this hook "
                         f"(sha256 {actual[:12]}, pinned {CHECKS_SHA256[:12]})")
    # CE-2.57. last_assistant_text returns "" both for an unreadable
    # transcript and for one with no reply text, and check() calls an empty
    # reply clean -- so either case used to pass silently. Neither is a
    # reply that was checked.
    try:
        with open(path, encoding="utf-8"):
            pass
        text = last_assistant_text(path)
    except OSError as e:
        return unchecked(f"transcript unreadable: {e.strerror}")
    except UnicodeDecodeError:
        return unchecked("transcript is not valid UTF-8 text")
    if not text.strip():
        return unchecked("no reply text found in the transcript")
    result = reply_rule_check.check(text, checks_path=checks_path)
    if result["status"] == "fired":
        print(json.dumps({"decision": "block",
                          "reason": reply_rule_check.block_reason(result["fired"])}))
        return 0
    if result["status"] == "unchecked":
        return unchecked(result["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
