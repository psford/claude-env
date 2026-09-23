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


def claude_project_slug(path):
    """The folder name Claude Code gives a project directory under
    ~/.claude/projects/: every character that is not a letter, digit or dash
    becomes a dash. CE-2.63: the first version turned only "/" into "-", so
    any path with a dot or underscore -- every dev worktree -- missed it.
    Observed: claude-env--CE-2.62 -> claude-env--CE-2-62, T-Tracker_win ->
    T-Tracker-win.
    """
    return re.sub(r"[^A-Za-z0-9-]", "-", str(path))


def default_memory_dir():
    """The live memory dir for this checkout, or REPLY_RULE_MEMORY_DIR."""
    override = os.environ.get("REPLY_RULE_MEMORY_DIR")
    if override:
        return Path(override)
    slug = claude_project_slug(REPO_ROOT)
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
    r"\b([A-Za-z0-9_.-]*(?:key|secret|token|password|passwd)[A-Za-z0-9_.-]*)"
    r"(\s*)([:=])(\s*)(\S+)",
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

    home directories, Bearer tokens, name=value / name: value secret
    assignments, email addresses, then any 24+ char [A-Za-z0-9_-] run
    holding both a letter and a digit.

    A secret assignment is any name CONTAINING key, secret, token,
    password or passwd (any case, compound names like AccountKey and
    x-api-token included) followed by = or : -- the whole value up to the
    next whitespace becomes [redacted], separators inside it and all.
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


def load_checks(path=CHECKS_PATH, data_bytes=None):
    """The checks from the data file: [{"rule", "question", "threshold"}].

    CE-2.63: when data_bytes is given it is parsed and the file is not read
    again -- the hook hashes the bytes against its pin and hands those same
    bytes here, so a file changed between the two reads cannot be trusted.

    Raises on a missing or malformed file -- check() turns that into an
    "unchecked" result with the reason.
    """
    if data_bytes is None:
        data_bytes = Path(path).read_bytes()
    data = json.loads(data_bytes.decode("utf-8"))
    checks = data["checks"]
    out = []
    for c in checks:
        out.append({"rule": c["rule"], "question": c["question"],
                    "threshold": float(c["threshold"])})
    return out


def validate_checks(checks):
    """Why the loaded checks cannot be trusted, or None when they can.

    Neutered-but-valid data -- no checks, an impossible threshold, a
    check with no question -- used to pass as clean. It is a normal
    operating state for NONE of those, so each is named here.
    """
    if not checks:
        return "checks data file has no checks"
    for c in checks:
        label = c.get("rule") or "<no rule>"
        if not str(c.get("rule") or "").strip():
            return "a check has an empty rule"
        if not str(c.get("question") or "").strip():
            return f"check {label} has an empty question"
        t = c.get("threshold")
        if isinstance(t, bool) or not isinstance(t, (int, float)) \
                or not 0 < float(t) < 1:
            return (f"check {label} threshold {t!r} is not "
                    "a number between 0 and 1")
    return None


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


def check(reply_text, memory_dir=None, client=None, checks_path=CHECKS_PATH,
          checks_bytes=None):
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
        checks = load_checks(checks_path, data_bytes=checks_bytes)
    except Exception as e:
        return {"status": "unchecked", "fired": [],
                "reason": f"could not read checks data file: {e}"}
    problem = validate_checks(checks)
    if problem:
        return {"status": "unchecked", "fired": [],
                "reason": f"invalid checks data file: {problem}"}

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
            if isinstance(p, bool) or not isinstance(p, (int, float)):
                return {"status": "unchecked", "fired": [],
                        "reason": (f"classifier answer for {c['rule']} "
                                   f"was not a number: {p!r}")}
            p = float(p)
            if not 0 <= p <= 1:
                return {"status": "unchecked", "fired": [],
                        "reason": (f"classifier answer for {c['rule']} "
                                   f"was not between 0 and 1: {p!r}")}
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


def _is_human_prompt(entry):
    """True for a message Patrick typed: a user entry that is not a tool
    result and not harness meta. A tool result also arrives as a user entry,
    and must not end the turn."""
    if entry.get("isMeta") or entry.get("isSidechain"):
        return False
    msg = entry.get("message")
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        kinds = {b.get("type") for b in content if isinstance(b, dict)}
        return "tool_result" not in kinds and "text" in kinds
    return False


STOP_HOOK_FEEDBACK = "Stop hook feedback:"


class BlockNotFound(Exception):
    """stop_hook_active was set, but no Stop hook's block is in this turn."""


def _is_stop_hook_feedback(entry):
    """True for the entry Claude Code writes when a Stop hook blocks: a meta
    user entry whose text starts "Stop hook feedback:"."""
    if not entry.get("isMeta"):
        return False
    msg = entry.get("message")
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return False
    content = msg.get("content")
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content
                          if isinstance(b, dict) and b.get("type") == "text")
    return isinstance(content, str) and content.startswith(STOP_HOOK_FEEDBACK)


def turn_texts(transcript_path, since_block=False):
    """Every assistant message with text since Patrick's last prompt.

    CE-2.63, the fourth CSO review: the hook used to score only the last
    assistant message, so in an ordinary multi-step turn -- say something,
    run a tool, say something else -- an ask in an earlier message went out
    unchecked. Each message is returned separately and checked on its own,
    as the measurement was taken: one message per question.

    since_block: a Stop hook has already blocked in this turn, and every
    message before that block was checked when it happened. Only messages
    after the latest block are returned, so a rewrite split across a tool
    call is checked in full and the replaced reply is never refused again.
    No block in the turn raises BlockNotFound.

    Raises OSError or UnicodeDecodeError; the hook turns each into an
    announced "unchecked".
    """
    entries = []
    with open(transcript_path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except ValueError:
                continue
    start = 0
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and _is_human_prompt(entry):
            start = i + 1
    if since_block:
        blocks = [i + 1 for i in range(start, len(entries))
                  if isinstance(entries[i], dict)
                  and _is_stop_hook_feedback(entries[i])]
        if not blocks:
            raise BlockNotFound("stop_hook_active is set but no Stop hook "
                                "feedback is recorded in this turn")
        start = blocks[-1]
    texts = []
    for entry in entries[start:]:
        msg = entry.get("message") if isinstance(entry, dict) else None
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        if entry.get("isSidechain"):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text")
        else:
            text = ""
        if text.strip():
            texts.append(text)
    return texts


def check_turn(texts, memory_dir=None, client=None, checks_path=CHECKS_PATH,
               checks_bytes=None):
    """check() on every message of the turn, concurrently, as one result.

    Each message is scored on its own -- joining them would change what was
    measured and let the 4000-character cut drop an early ask. Calls run in
    parallel so a turn of many messages costs about one call's latency.

    fired if any message fired (every rule that fired, once, at its highest
    score); otherwise unchecked if any message could not be checked, with
    that reason; otherwise clean. An empty turn is unchecked: there was
    nothing to check, which is not the same as nothing wrong.
    """
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return {"status": "unchecked", "fired": [],
                "reason": "no reply text in this turn"}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(8, len(texts))) as pool:
        results = list(pool.map(
            lambda t: check(t, memory_dir=memory_dir, client=client,
                            checks_path=checks_path, checks_bytes=checks_bytes),
            texts))
    fired = {}
    for r in results:
        for f in r["fired"]:
            if f["rule"] not in fired or f["score"] > fired[f["rule"]]["score"]:
                fired[f["rule"]] = f
    if fired:
        return {"status": "fired", "fired": list(fired.values()), "reason": ""}
    for r in results:
        if r["status"] == "unchecked":
            return {"status": "unchecked", "fired": [], "reason": r["reason"]}
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
