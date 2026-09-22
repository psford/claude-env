#!/usr/bin/env python3
"""Check an outgoing reply against the measured reply-rule checks (CE-2.56).

Round 3, after the CSO review (docs/reviews/2026-09-21-reply-rule-guard-infosec.md).

Every non-empty reply is checked -- there is no shape gate. The question,
its threshold and the measurement behind them live in
helpers/data/reply_rule_checks.json -- the question text exists ONLY there,
so the question in use is always the one that was measured.

What leaves the machine: the reply is scrubbed first (home paths, bearer
tokens, key=value secrets, emails, key-shaped strings), and only then cut to
its last 4000 characters -- scrubbing before the cut means a secret that
straddles the cut is never half-sent.

check() returns one of three statuses, never a silent fourth:
  fired      -- at least one check scored at or above its threshold.
  clean      -- nothing fired (an empty reply is clean).
  unchecked  -- the check could not run (no key, network error, classifier
                error, missing data file, missing memory note), with a plain
                reason. The reply is NOT blocked -- a broken classifier must
                never stop every reply -- but the session is told.

Usage:
    python3 helpers/reply_rule_check.py --check-file reply.txt
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_health_check import TypeSafeClient, load_api_key  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def default_memory_dir():
    """The live memory dir for this checkout, or REPLY_RULE_MEMORY_DIR.

    <slug> is the repo root path with every "/" replaced by "-" -- the same
    slug Claude Code derives -- so no machine-local path is baked in.
    """
    override = os.environ.get("REPLY_RULE_MEMORY_DIR")
    if override:
        return Path(override)
    slug = str(REPO_ROOT).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug / "memory"


CHECKS_PATH = Path(__file__).resolve().parent / "data" / "reply_rule_checks.json"

FRONTMATTER_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M)
HOW_TO_APPLY_RE = re.compile(r"\*\*How to apply:\*\*\s*\n")

MAX_STATE_CHARS = 4000

HOME_PATH_RE = re.compile(
    r"(?:(?:/home|/Users)/[A-Za-z0-9_.-]+|[Cc]:\\Users\\[A-Za-z0-9_.-]+)"
)
BEARER_RE = re.compile(r"\bBearer\s+\S+")
SECRET_ASSIGN_RE = re.compile(
    r"\b(password|passwd|secret|token|api_key|api-key|key)\b(\s*)([:=])(\s*)(\S+)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{24,}")


def _redact_long_token(m):
    """[redacted] only when the run mixes letters and digits."""
    run = m.group(0)
    has_letter = any(c.isalpha() for c in run)
    has_digit = any(c.isdigit() for c in run)
    return "[redacted]" if (has_letter and has_digit) else run


def scrub(text):
    """Secret-shaped and identifying strings replaced, in this order:

    home directories, Bearer tokens, key=value assignments, email
    addresses, then any 24+ char [A-Za-z0-9_-] run holding both a letter
    and a digit.
    """
    text = HOME_PATH_RE.sub("~", text)
    text = BEARER_RE.sub("Bearer [redacted]", text)
    text = SECRET_ASSIGN_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}[redacted]",
        text,
    )
    text = EMAIL_RE.sub("[email]", text)
    text = LONG_TOKEN_RE.sub(_redact_long_token, text)
    return text


def make_state(reply_text):
    """What is sent to the classifier: scrub the WHOLE reply, then keep its
    last MAX_STATE_CHARS characters. Still a plain string."""
    return scrub(reply_text)[-MAX_STATE_CHARS:]


def load_checks(path=CHECKS_PATH):
    """The checks from the data file: [{"rule", "question", "threshold"}].

    Raises on a missing or malformed file -- check() turns that into an
    "unchecked" result with the reason.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    checks = data["checks"]
    out = []
    for c in checks:
        out.append({"rule": c["rule"], "question": c["question"],
                    "threshold": float(c["threshold"])})
    return out


def load_memory(memory_path):
    """One memory file as {"key", "desc", "how_to_apply"}.

    "how_to_apply" is the bullet list under "**How to apply:**" -- the
    concrete instructions the block quotes back, so the fix is obvious.
    Returns None when the file does not exist or cannot be read.
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


def score_check(state, question, client):
    """One noul: instructions = the question, NO criteria, state = the
    scrubbed reply text as a plain string. Returns the probability."""
    answers = client.ask(state,
                         {"c0": {"type": "noul", "instructions": question}},
                         retries=1, timeout=10)
    return answers["c0"]


def check(reply_text, memory_dir=None, client=None, checks_path=CHECKS_PATH):
    """Score this reply against every measured check.

    Returns {"status": "fired"|"clean"|"unchecked", "fired": [...],
    "reason": str}. "unchecked" carries a plain reason for every case where
    the check cannot run; a violation is the only thing that fires.
    """
    if memory_dir is None:
        memory_dir = default_memory_dir()
    if not reply_text or not reply_text.strip():
        return {"status": "clean", "fired": [], "reason": ""}

    try:
        checks = load_checks(checks_path)
    except Exception as e:
        return {"status": "unchecked", "fired": [],
                "reason": f"could not read checks data file: {e}"}
    if not checks:
        return {"status": "clean", "fired": [], "reason": ""}

    try:
        if client is None:
            client = TypeSafeClient(load_api_key(default_env_file()))
    except Exception as e:
        return {"status": "unchecked", "fired": [],
                "reason": f"no classifier key: {e}"}

    memories = {}
    for c in checks:
        mem_err = None
        try:
            mem = load_memory(Path(memory_dir) / f"{c['rule']}.md")
        except OSError as e:
            mem = None
            mem_err = e
        if mem is None:
            # A check whose memory file is gone cannot quote its own
            # instruction; announce rather than block namelessly.
            detail = f" (unreadable: {mem_err})" if mem_err else ""
            return {"status": "unchecked", "fired": [],
                    "reason": f"missing memory note for rule {c['rule']}"
                              f"{detail}"}
        memories[c["rule"]] = mem

    state = make_state(reply_text)
    fired = []
    try:
        for c in checks:
            p = score_check(state, c["question"], client)
            if not isinstance(p, (int, float)):
                continue
            p = float(p)
            if p >= c["threshold"]:
                mem = memories[c["rule"]]
                fired.append({**mem, "rule": c["rule"],
                              "score": round(p, 3),
                              "threshold": c["threshold"]})
    except Exception as e:
        return {"status": "unchecked", "fired": [],
                "reason": f"classifier did not answer: {e}"}

    if fired:
        return {"status": "fired", "fired": fired, "reason": ""}
    return {"status": "clean", "fired": [], "reason": ""}


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
    return REPO_ROOT / ".env"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-file", type=Path,
                    help="score this file's text as a reply and print findings")
    ap.add_argument("--memory-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.check_file:
        result = check(args.check_file.read_text(encoding="utf-8"),
                       memory_dir=args.memory_dir)
        if result["status"] == "fired":
            print(block_reason(result["fired"]))
            return 1
        if result["status"] == "unchecked":
            print(f"reply NOT checked -- {result['reason']}", file=sys.stderr)
            return 2
        print("no rule fired")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
