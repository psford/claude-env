#!/usr/bin/env python3
"""Scan every saved memory against a consequential action (CE-2.69).

Patrick, 2026-09-24: the orchestrator holds memories it has been over dozens
of times and still breaks them. This module puts the matching rules in front
of the actor BEFORE the action runs, not after the reply is written.

One request per scan: a single choice question whose options are every
memory key (description cut to 150 characters) plus "none". The action text
is scrubbed by the same scrub() the reply-rule check uses -- what leaves the
machine never holds a home path or a token.

Three outcomes, never a silent fourth:
  fired      -- at least one rule surfaced (probability >= 0.10, top three).
  clean      -- nothing worth surfacing, or "none" itself scored >= 0.60.
  unchecked  -- the scan could not run (no key, network error, too many
                memories), with a plain reason. A broken classifier must
                never block an action.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_health_check import TypeSafeClient, load_api_key, load_memories  # noqa: E402
from reply_rule_check import default_env_file, default_memory_dir, scrub  # noqa: E402

HOW_TO_APPLY_RE = re.compile(r"\*\*How to apply:\*\*")
HEADING_OR_RELATED_RE = re.compile(r"^(?:\*\*|Related:)")

MAX_HOW_CHARS = 600
MAX_DESC_CHARS = 150
MAX_STATE_CHARS = 4000
MAX_MEMORIES = 254  # plus "none" = 255, the choice cap
SURFACE_PROB = 0.10
# scrub() collapses "/home/<user>" to "~" but leaves the path after it --
# an action's state must not leak any part of a home path, not just the
# prefix (AC2). The rest of the ~-relative path goes too.
HOME_REMNANT_RE = re.compile(r"~/[^\s\"']*")
NONE_CONFIDENT_PROB = 0.60
NONE_DESC = ("No saved rule applies: an ordinary read, check, status report "
             "or routine step.")

RULE_QUESTION = ("Which saved rule most applies to this action, the one the "
                 "actor should re-read before doing it? Answer none if it "
                 "is an ordinary step.")


def how_to_apply(body):
    """The "**How to apply:**" section of a memory body -- the text after
    the marker, stopping before a "Related:" line or the next "**" heading,
    capped at MAX_HOW_CHARS. A body without the marker yields its first
    MAX_HOW_CHARS characters.
    """
    m = HOW_TO_APPLY_RE.search(body)
    if not m:
        return body.strip()[:MAX_HOW_CHARS]
    lines = []
    for line in body[m.end():].splitlines():
        if HEADING_OR_RELATED_RE.match(line.strip()) and lines:
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    return text[:MAX_HOW_CHARS]


def scan(action_text, memory_dir=None, client=None):
    """One Jev request over every saved memory, against one action.

    Returns {"status": "fired"|"clean"|"unchecked", "rules": [...],
    "reason": str}. Each surfaced rule is {"key", "desc", "p",
    "how_to_apply"}.
    """
    if memory_dir is None:
        memory_dir = default_memory_dir()
    try:
        memories = load_memories(memory_dir)
    except Exception as e:
        return {"status": "unchecked", "rules": [],
                "reason": f"could not read memories: {e}"}
    if len(memories) > MAX_MEMORIES:
        return {"status": "unchecked", "rules": [],
                "reason": (f"{len(memories)} memories exceeds the "
                           f"{MAX_MEMORIES}-option choice cap; no tournament "
                           "is built for a scan that must stay one request")}

    options = {m["key"]: (m["desc"] or m["key"])[:MAX_DESC_CHARS]
               for m in memories}
    options["none"] = NONE_DESC

    try:
        if client is None:
            client = TypeSafeClient(load_api_key(default_env_file()))
    except Exception as e:
        return {"status": "unchecked", "rules": [],
                "reason": f"no classifier key: {e}"}

    state = {"action": HOME_REMNANT_RE.sub(
        "~[redacted]", scrub(action_text))[-MAX_STATE_CHARS:]}
    question = {"c0": {"type": "choice", "instructions": RULE_QUESTION,
                       "criteria": options}}
    try:
        answers = client.ask(state, question, retries=1, timeout=12)
        pick, _confidence, probabilities = answers["c0"]
    except Exception as e:
        return {"status": "unchecked", "rules": [],
                "reason": f"classifier did not answer: {e}"}

    probs = probabilities or {}
    for k, v in probs.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return {"status": "unchecked", "rules": [],
                    "reason": (f"classifier probability for {k} was not a "
                               f"number: {v!r}")}
    if probs.get("none", 0.0) >= NONE_CONFIDENT_PROB:
        return {"status": "clean", "rules": [], "reason": ""}

    by_key = {m["key"]: m for m in memories}
    ranked = sorted(
        ((k, float(p)) for k, p in probs.items()
         if k != "none" and k in by_key and float(p) >= SURFACE_PROB),
        key=lambda kv: -kv[1])[:3]
    rules = [{"key": k, "desc": by_key[k]["desc"], "p": round(p, 3),
              "how_to_apply": how_to_apply(by_key[k]["body"])}
             for k, p in ranked]
    if rules:
        return {"status": "fired", "rules": rules, "reason": ""}
    return {"status": "clean", "rules": [], "reason": ""}


def context_lines(rules):
    """The additionalContext body for surfaced rules."""
    lines = ["Jev scanned your saved memories for this action. "
             "Re-read before you proceed:"]
    for r in rules:
        lines.append(f"- {r['key']} ({r['p']:.2f}): {r['how_to_apply']}")
    return "\n".join(lines)
