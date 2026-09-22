#!/usr/bin/env python3
"""Stop hook: a decision that is Patrick's goes on the board, not in chat.

CE-2.55. Patrick, 2026-09-21: "I want you to figure out a way to use jev so
you stop ignoring memories we've been over dozens of times." The memory
broken most often, while held, was feedback_ask_on_the_board_and_wait: asking
him to approve something that is his by rule -- removing a criterion, new
test infrastructure, reopening a ticket -- in a chat message that ends on a
question, instead of `ticket ask` and a stop.

This file is thin on purpose. The question, its threshold and the
measurement behind them live in helpers/data/reply_rule_checks.json; the
logic lives in helpers/reply_rule_check.py. The last reply is read by the
same function verification_claim_guard uses, imported rather than copied.

Fails open: no key, no network, or a Jev error means no block. A detected
violation above its measured threshold blocks.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "helpers"))

from verification_claim_guard import last_assistant_text  # noqa: E402
import reply_rule_check  # noqa: E402


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    path = data.get("transcript_path")
    if not path:
        return 0
    fired = reply_rule_check.check_reply(last_assistant_text(path))
    if not fired:
        return 0
    print(json.dumps({"decision": "block",
                      "reason": reply_rule_check.block_reason(fired)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
