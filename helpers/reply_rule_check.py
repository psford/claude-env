#!/usr/bin/env python3
"""Check an outgoing reply against the measured reply-rule checks (CE-2.55).

Round 1 scored a reply against all 92 feedback memories and subtracted fitted
base rates. Its own live run showed the miss: the rule this exists for scored
0.74 on a real violating reply against a 0.73 baseline, because that rule
reads as near-violated on almost every reply and the calibration erased it.

Round 2 asks ONE targeted question per check, and fires only above a measured
threshold. The question, the threshold and the measurement behind them live in
helpers/data/reply_rule_checks.json -- the question text exists ONLY there, so
the question in use is always the one that was measured. That file was
calibrated on replies Patrick accepted and objected to (dev set + held-out
set, 3 runs each); the threshold sits midway between the highest clean score
and the lowest flagged score.

Population gate: only a reply whose last non-empty line ends with "?" is ever
sent to Jev. That is the population the question was measured on.

Fail open on the classifier, closed on a violation: no key, no network, a Jev
error, a missing data file or a missing memory file means NO block -- a broken
classifier must never stop every reply in a session.

Usage:
    python3 helpers/reply_rule_check.py --check-file reply.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_health_check import TypeSafeClient, load_api_key  # noqa: E402

LIVE_MEMORY_DIR = Path(
    "/home/patrick/.claude/projects/-home-patrick-projects-claude-env/memory"
)
CHECKS_PATH = Path(__file__).resolve().parent / "data" / "reply_rule_checks.json"

FRONTMATTER_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M)
HOW_TO_APPLY_RE = re.compile(r"\*\*How to apply:\*\*\s*\n")


def load_checks(path=CHECKS_PATH):
    """The checks from the data file: [{"rule", "question", "threshold"}].

    Raises on a missing or malformed file -- callers that must fail open
    catch it (check_reply does).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    checks = data["checks"]
    out = []
    for c in checks:
        out.append({"rule": c["rule"], "question": c["question"],
                    "threshold": float(c["threshold"])})
    return out


def ends_with_question(reply_text):
    """True when the last non-empty line ends with "?" (trailing "*" ignored).

    That is the population the checks were measured on; anything else is
    never sent to Jev.
    """
    if not reply_text:
        return False
    lines = [ln for ln in reply_text.splitlines() if ln.strip()]
    if not lines:
        return False
    return lines[-1].rstrip().rstrip("*").rstrip().endswith("?")


def load_memory(memory_path):
    """One memory file as {"key", "desc", "how_to_apply"}.

    "how_to_apply" is the bullet list under "**How to apply:**" -- the
    concrete instructions the block quotes back, so the fix is obvious.
    Returns None when the file does not exist or has no description.
    """
    p = Path(memory_path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    d = FRONTMATTER_DESC_RE.search(text)
    desc = d.group(1).strip().strip('"') if d else p.stem
    how = ""
    m = HOW_TO_APPLY_RE.search(text)
    if m:
        lines = []
        for line in text[m.end():].splitlines():
            if line.startswith("-") or (lines and line.startswith((" ", "\t"))):
                lines.append(line)
            elif not line.strip() and not lines:
                continue
            else:
                break
        how = "\n".join(lines).strip()
    return {"key": p.stem, "desc": desc, "how_to_apply": how}


def score_check(reply_text, question, client):
    """One noul: instructions = the question, NO criteria, state = the reply
    text itself as a plain string. Returns the probability. Raises whatever
    the client raises."""
    answers = client.ask(
        reply_text,
        {"c0": {"type": "noul", "instructions": question}},
    )
    return answers["c0"]


def check_reply(reply_text, memory_dir=LIVE_MEMORY_DIR, client=None,
                checks_path=CHECKS_PATH):
    """The checks this reply trips. Empty list = no block, ALWAYS.

    Fail open on the classifier: any error -- no key, no network, bad JSON,
    a missing data file or a missing memory file -- returns [] rather than
    blocking. A check fires only at or above its measured threshold.
    """
    if not reply_text or not reply_text.strip():
        return []
    if not ends_with_question(reply_text):
        return []
    try:
        checks = load_checks(checks_path)
        if not checks:
            return []
        memories = {}
        for c in checks:
            mem = load_memory(Path(memory_dir) / f"{c['rule']}.md")
            if mem is None:
                # A check whose memory file is gone cannot quote its own
                # instruction; fail open rather than block namelessly.
                return []
            memories[c["rule"]] = mem
        if client is None:
            client = TypeSafeClient(load_api_key(default_env_file()))
        fired = []
        for c in checks:
            p = score_check(reply_text, c["question"], client)
            if not isinstance(p, (int, float)):
                continue
            p = float(p)
            if p >= c["threshold"]:
                mem = memories[c["rule"]]
                fired.append({**mem, "rule": c["rule"],
                              "score": round(p, 3),
                              "threshold": c["threshold"]})
        return fired
    except Exception:
        return []


def block_reason(fired):
    """The text the hook prints for the fired checks."""
    parts = []
    for f in fired:
        parts.append(
            f"BLOCKED BY {f['rule']} "
            f"(score {f['score']:.2f} >= threshold {f['threshold']:.2f})\n"
            f"{f['desc']}\n\n"
            f"How to apply:\n{f['how_to_apply']}"
        )
    fix = ('Fix: do not ask this in chat. Put the question on the board with '
           '`ticket ask <ID> --question "..."` and STOP -- wait for the '
           'answer instead of sending this reply.')
    return "\n\n".join(parts + [fix])


def default_env_file():
    return Path(__file__).resolve().parent.parent / ".env"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-file", type=Path,
                    help="score this file's text as a reply and print findings")
    ap.add_argument("--memory-dir", type=Path, default=LIVE_MEMORY_DIR)
    args = ap.parse_args(argv)

    if args.check_file:
        fired = check_reply(args.check_file.read_text(encoding="utf-8"),
                            memory_dir=args.memory_dir)
        if not fired:
            print("no rule fired")
            return 0
        print(block_reason(fired))
        return 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
