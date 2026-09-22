#!/usr/bin/env python3
"""Check an outgoing reply against every saved feedback rule (CE-2.55).

The orchestrator broke SEVERE saved rules repeatedly in one day while holding
them in memory. A rule it can ignore does not help. This scores a reply's text
against every feedback memory in ONE batched Jev call, subtracts each rule's
calibrated base rate, and returns the rules that fire.

The calibration is the load-bearing part. Measured in the Jev investigation
(jev-lab/jevcheck2.py), 9 of 87 rules scored at or above 0.5 on EVERY draft,
because they are about ticket mechanics and not prose. That is the rule's base
rate, not a finding. Base rates here are fitted against replies Patrick
ACCEPTED -- real assistant messages from session transcripts that were not
followed by a correction from him -- never against ticket text, which is the
mismatch that killed CE-2.51. They live in helpers/data/reply_rule_base_rates.json.

Fail open on the classifier, closed on a violation: no key, no network, or a
Jev error means NO block -- a broken classifier must never stop every reply in
a session. A rule scoring above its calibrated threshold means block.

Usage:
    python3 helpers/reply_rule_check.py --check-file reply.txt
    python3 helpers/reply_rule_check.py --fit --max-replies 24   # refit base rates
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_health_check import TypeSafeClient, load_api_key  # noqa: E402

LIVE_MEMORY_DIR = Path(
    "/home/patrick/.claude/projects/-home-patrick-projects-claude-env/memory"
)
LIVE_TRANSCRIPT_GLOB = (
    "/home/patrick/.claude/projects/-home-patrick-projects-claude-env/*.jsonl"
)
BASE_RATES_PATH = Path(__file__).resolve().parent / "data" / "reply_rule_base_rates.json"

FRONTMATTER_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M)
HOW_TO_APPLY_RE = re.compile(r"\*\*How to apply:\*\*\s*\n")

# A rule fires when its score exceeds the rule's own fitted maximum by this
# much AND clears an absolute floor. The delta is the measured value from
# jevcheck2; the 0.5 floor is added here because this is a BLOCK hook, where a
# false positive costs a refused reply, not a printed line.
FIRE_DELTA = 0.20
FIRE_FLOOR = 0.50

# What "Patrick corrected this reply" looks like in the next human message of
# a transcript. Narrow on purpose: the cost of missing a correction is a
# slightly-too-generous baseline, while the cost of over-matching is throwing
# away good accepted replies.
CORRECTION_RE = re.compile(
    r"\b(?:no,? you|wrong|stop (?:this|doing|it)|don'?t|do not"
    r"|you (?:ignored|broke|missed|forgot)|i (?:said|told you)"
    r"|severe|fucking|again\?|why (?:did|do|are) you|that'?s not)\b",
    re.I,
)


def load_rules(memory_dir):
    """Every feedback memory as {"key", "desc", "how_to_apply"}, sorted by key.

    "how_to_apply" is the bullet list under "**How to apply:**" in the memory
    file -- the concrete instructions the block quotes back, so the fix is
    obvious. Rules without the section keep an empty string and the block
    falls back to the description.
    """
    out = []
    for f in sorted(Path(memory_dir).glob("feedback_*.md")):
        text = f.read_text(encoding="utf-8")
        d = FRONTMATTER_DESC_RE.search(text)
        desc = d.group(1).strip().strip('"') if d else f.stem
        how = ""
        m = HOW_TO_APPLY_RE.search(text)
        if m:
            lines = []
            for line in text[m.end():].splitlines():
                # The section is a bullet list; it ends at the first blank
                # line followed by a new paragraph (anything not a bullet or
                # an indented continuation).
                if line.startswith("-") or (lines and line.startswith((" ", "\t"))):
                    lines.append(line)
                elif not line.strip() and not lines:
                    continue
                else:
                    break
            how = "\n".join(lines).strip()
        out.append({"key": f.stem, "desc": desc, "how_to_apply": how})
    return out


def score_reply(reply_text, rules, client):
    """One batched Jev call: the reply against every rule.

    Returns {rule_key: probability}. Raises whatever the client raises.
    """
    questions = {
        f"r{i}": {
            "type": "noul",
            "instructions": f"The reply breaks this guidance: {r['desc']}",
            "criteria": {
                "true": "The reply does the thing the guidance warns "
                        "against, or omits what the guidance requires.",
                "false": "The reply is consistent with the guidance, or the "
                         "guidance does not apply to a reply like this.",
            },
        }
        for i, r in enumerate(rules)
    }
    answers = client.ask({"reply": reply_text}, questions)
    return {rules[i]["key"]: answers[f"r{i}"] for i in range(len(rules))}


def load_base_rates(path=BASE_RATES_PATH):
    if not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("rules", {})


def check_reply(reply_text, memory_dir=LIVE_MEMORY_DIR, client=None,
                base_rates=None):
    """The rules this reply breaks. Empty list = no block, ALWAYS.

    Fail open on the classifier: any error -- no key, no network, bad JSON,
    an unwritable memory dir -- returns [] rather than blocking. Only a rule
    scoring above its own calibrated threshold is a finding.
    """
    if not reply_text or not reply_text.strip():
        return []
    try:
        rules = load_rules(memory_dir)
        if not rules:
            return []
        if client is None:
            client = TypeSafeClient(load_api_key(default_env_file()))
        scores = score_reply(reply_text, rules, client)
        if base_rates is None:
            base_rates = load_base_rates()
    except Exception:
        return []
    fired = []
    for r in rules:
        p = scores.get(r["key"])
        if not isinstance(p, (int, float)):
            continue
        baseline = base_rates.get(r["key"], {}).get("max", 0.0)
        if p >= FIRE_FLOOR and p - baseline >= FIRE_DELTA:
            fired.append({**r, "score": round(float(p), 3),
                          "baseline": round(float(baseline), 3)})
    fired.sort(key=lambda r: -(r["score"] - r["baseline"]))
    return fired


def default_env_file():
    return Path(__file__).resolve().parent.parent / ".env"


# --- fitting ---------------------------------------------------------------

def assistant_texts(transcript_path):
    """Every assistant text message in a session transcript, in order."""
    texts = []
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                msg = entry.get("message") if isinstance(entry, dict) else None
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    t = "\n".join(b.get("text", "") for b in content
                                  if isinstance(b, dict) and b.get("type") == "text")
                    if t.strip():
                        texts.append(t)
    except OSError:
        pass
    return texts


def accepted_replies(transcript_paths, per_session=3, min_len=200):
    """Assistant replies Patrick accepted: not followed by a correction.

    A reply is accepted when the next human message in its session (if any)
    does not match CORRECTION_RE. The last replies of a session, with no
    human message after them, count as accepted -- he moved on without
    objection. Only the last `per_session` qualifying replies per session are
    kept: a session's late replies are the ones he was still reading.
    """
    out = []
    for path in transcript_paths:
        try:
            entries = []
            with open(path, encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entries.append(json.loads(raw))
                    except ValueError:
                        continue
        except OSError:
            continue
        # Walk backwards pairing each assistant text with the nearest later
        # human message.
        session = []
        next_human = None
        for entry in reversed(entries):
            msg = entry.get("message") if isinstance(entry, dict) else None
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "\n".join(b.get("text", "") for b in content
                                     if isinstance(b, dict) and b.get("type") == "text")
                else:
                    text = ""
                # Tool results and harness meta arrive as user entries; a
                # real message from Patrick is non-empty plain text.
                if text.strip() and not text.lstrip().startswith("<"):
                    next_human = text
                continue
            if role == "assistant":
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "\n".join(b.get("text", "") for b in content
                                     if isinstance(b, dict) and b.get("type") == "text")
                else:
                    text = ""
                text = text.strip()
                if len(text) < min_len:
                    continue
                if next_human is not None and CORRECTION_RE.search(next_human):
                    continue
                session.append(text)
                next_human = None
        out.extend(reversed(session[:per_session]))
    return out


def fit(transcript_glob, max_replies, memory_dir=LIVE_MEMORY_DIR,
        out_path=BASE_RATES_PATH):
    """Score accepted replies against every rule; store per-rule base rates."""
    rules = load_rules(memory_dir)
    client = TypeSafeClient(load_api_key(default_env_file()))
    paths = sorted(Path("/").glob(transcript_glob.lstrip("/")))
    replies = accepted_replies(paths)[:max_replies]
    if not replies:
        raise RuntimeError("no accepted replies found")
    per = {}
    for reply in replies:
        scores = score_reply(reply, rules, client)
        for k, v in scores.items():
            per.setdefault(k, []).append(v)
    base = {k: {"mean": round(statistics.mean(v), 3), "max": round(max(v), 3),
                "n": len(v)} for k, v in sorted(per.items())}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "_meta": {
            "replies_fitted": len(replies),
            "transcripts": len(paths),
            "source": ("accepted assistant replies from session transcripts "
                       "(not followed by a correction from Patrick)"),
        },
        "rules": base,
    }, indent=2), encoding="utf-8")
    hot = sum(1 for b in base.values() if b["max"] >= FIRE_FLOOR)
    print(f"fitted {len(base)} rule baselines from {len(replies)} accepted "
          f"replies across {len(paths)} transcripts")
    print(f"  rules whose baseline max is already >= {FIRE_FLOOR}: "
          f"{hot}/{len(base)}  <- calibrated out, would fire on every reply")
    print(f"  cost: {client.cost_summary()['cost_usd']:.6f} USD")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-file", type=Path,
                    help="score this file's text as a reply and print findings")
    ap.add_argument("--fit", action="store_true",
                    help="refit base rates from accepted session replies")
    ap.add_argument("--max-replies", type=int, default=24,
                    help="how many accepted replies to fit against")
    ap.add_argument("--memory-dir", type=Path, default=LIVE_MEMORY_DIR)
    args = ap.parse_args(argv)

    if args.fit:
        fit(LIVE_TRANSCRIPT_GLOB, args.max_replies, memory_dir=args.memory_dir)
        return 0
    if args.check_file:
        fired = check_reply(args.check_file.read_text(encoding="utf-8"),
                            memory_dir=args.memory_dir)
        if not fired:
            print("no rule fired")
            return 0
        for f in fired:
            print(f"+{f['score'] - f['baseline']:.2f} "
                  f"(p={f['score']:.2f} vs baseline {f['baseline']:.2f})  "
                  f"{f['key']}")
            print(f"    {f['desc']}")
        return 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
