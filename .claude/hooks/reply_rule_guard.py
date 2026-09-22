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
        print("reply_rule_guard: reply NOT checked -- hook input was not JSON",
              file=sys.stderr)
        return 1
    path = data.get("transcript_path")
    if not path:
        print("reply_rule_guard: reply NOT checked -- no transcript_path in "
              "hook input", file=sys.stderr)
        return 1
    result = reply_rule_check.check(last_assistant_text(path))
    if result["status"] == "fired":
        print(json.dumps({"decision": "block",
                          "reason": reply_rule_check.block_reason(result["fired"])}))
        return 0
    if result["status"] == "unchecked":
        print(f"reply_rule_guard: reply NOT checked -- {result['reason']}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
