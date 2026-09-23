#!/usr/bin/env python3
"""Health check for the Claude Code memory store (CE-2.49).

The memory store is a directory of markdown notes, each with a frontmatter
`description:` and a body that cross-references other notes with
`[[snake_case_key]]` links. Nothing had ever checked it: measured 2026-09-20,
55 of its cross-references did not resolve (repaired by hand the same day).
This is the check that stops that recurring.

Two passes:

  structural (free, no model, no network)
    - dead [[links]]: a link naming no existing memory file.
    - dead cited paths: a backtick-quoted, ~/ or /home/-rooted filesystem
      path that no longer exists. Deliberately narrow: an earlier version of
      this check tried to resolve bare relative citations (`foo.py`,
      `src/bar.ts`) by globbing one level under ~/projects, and that guessed
      wrong often enough to be useless -- illustrative filenames in prose,
      generic examples, and paths that belong to a different repo than the
      one the glob happened to match all came back "dead" when they were
      fine. An absolute path rooted at ~/ or /home/ has exactly one place it
      can resolve, so it is the only citation shape this check claims
      anything about. Relative citations and non-filesystem absolute paths
      (e.g. `/api/auth/login`, `/etc/fstab`) are not reported either way.

  overlap (costs a few cents, needs TYPESAFE_API_KEY)
    - for each memory, one Choice question across every other memory's
      description, asking which covers the same ground. One Choice beats N
      Nouls for ranking this (measured: see jev-lab/FINDINGS.md) -- a flat
      field of probabilities means nothing overlaps, which is the common
      case. Choice caps at 255 options; above that this chunks into a
      tournament (round of <=255-option Choices, keep each winner, repeat).

Usage:
    python3 helpers/memory_health_check.py             # both passes
    python3 helpers/memory_health_check.py --quick      # structural only
    python3 helpers/memory_health_check.py --json        # machine-readable
    python3 helpers/memory_health_check.py --memory-dir /path/to/fixture

Exit codes:
    0  structural check clean (no dead links, no dead paths)
    1  a dead link or a dead path was found
    2  a configuration/operational error (bad --memory-dir, missing API key)
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LIVE_MEMORY_DIR = Path(
    "/home/patrick/.claude/projects/-home-patrick-projects-claude-env/memory"
)

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
# Jev's Cloudflare refuses urllib's default User-Agent with HTTP 403
# (error 1010), measured 2026-09-22; a named one gets through. Public
# repo: no personal domain or email in this string.
USER_AGENT = "claude-env-typesafe-client/1.0"
TYPESAFE_MODEL = "jev-latest"
# Measured 2026-09-19 against jev-1.13.0 (jev-lab/FINDINGS.md) -- input-token
# rate only, matching the prototype's own cost() calculation.
TYPESAFE_COST_PER_INPUT_TOKEN = 0.042 / 1e6

CHOICE_MAX_OPTIONS = 255

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
# A ticket id (CH-224.10, CE-2.49, NFL-2.5) written inside [[...]] is not a
# dead link -- it was never meant to resolve to a memory. Every real memory
# key is lowercase snake_case with no hyphen, so this shape is unambiguous:
# it never collides with a real key, and it still lets a genuine
# hyphen-for-underscore typo (the majority of the 55 that started this
# story) fail the ticket-id shape and get reported as dead, same as before.
TICKET_ID_RE = re.compile(r"^[A-Z]{1,10}-\d+(?:\.\d+)?$")

FRONTMATTER_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M)

# Only a backtick-quoted, ~/ or /home/-rooted path. See the module docstring
# for why relative citations and other absolute paths are not resolved.
FS_PATH_RE = re.compile(r"`(~(?:/[\w.\-]+)+|/home(?:/[\w.\-]+)+)`")


def load_memories(memory_dir):
    """Read every memory note under memory_dir (excluding the MEMORY.md index).

    Returns a list of {"key", "path", "desc", "body"} dicts, ordered by key.
    """
    out = []
    for f in sorted(Path(memory_dir).glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        text = f.read_text(encoding="utf-8")
        d = FRONTMATTER_DESC_RE.search(text)
        desc = d.group(1).strip().strip('"') if d else ""
        # Frontmatter is "---\n...\n---\nbody"; split(sep, 2) stops after the
        # second "---" so a literal "---" later in the body (e.g. a markdown
        # rule) stays part of the body instead of truncating it.
        body = text.split("---", 2)[-1]
        out.append({"key": f.stem, "path": f, "desc": desc, "body": body})
    return out


def find_dead_links(memories):
    """[[links]] naming no existing memory, excluding ticket-id-shaped ones."""
    keys = {m["key"] for m in memories}
    out = []
    for m in memories:
        for link in sorted(set(LINK_RE.findall(m["body"]))):
            if TICKET_ID_RE.match(link):
                continue
            if link not in keys:
                out.append({"memory": m["key"], "link": link})
    return out


def find_dead_paths(memories):
    """Backtick-quoted ~/ or /home/-rooted paths that no longer exist."""
    out = []
    home = str(Path.home())
    for m in memories:
        for raw in sorted(set(FS_PATH_RE.findall(m["body"]))):
            resolved = Path(raw.replace("~", home, 1)) if raw.startswith("~") else Path(raw)
            if not resolved.exists():
                out.append({"memory": m["key"], "path": raw})
    return out


class TypeSafeClient:
    """Minimal stdlib-only TypeSafe/Jev client -- self-contained, no SDK."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0}

    def ask(self, state, questions, retries=5, timeout=120):
        """Send one request. Returns {qid: simplified_value}.

        retries/timeout bound the wait: timeout seconds per attempt, retries
        attempts total, no sleep after the final one.
        """
        body = json.dumps(
            {"model": TYPESAFE_MODEL, "state": state, "questions": questions}
        ).encode()
        last_err = None
        for attempt in range(retries):
            req = urllib.request.Request(
                TYPESAFE_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.loads(r.read())
                self.usage["calls"] += 1
                self.usage["input_tokens"] += out.get("usage", {}).get("input_tokens", 0)
                self.usage["output_tokens"] += out.get("usage", {}).get("output_tokens", 0)
                return {k: _simplify(v) for k, v in out["answers"].items()}
            except urllib.error.HTTPError as e:
                last_err = e
                detail = e.read()[:400].decode(errors="replace")
                if e.code in (429, 500, 502, 503, 529):
                    if attempt < retries - 1:
                        time.sleep((2 ** attempt) + random.random())
                    continue
                self.usage["errors"] += 1
                raise RuntimeError(f"HTTP {e.code}: {detail}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                if attempt < retries - 1:
                    time.sleep((2 ** attempt) + random.random())
        self.usage["errors"] += 1
        raise RuntimeError(f"exhausted retries: {last_err}")

    def cost_summary(self):
        input_tokens = self.usage["input_tokens"]
        cost = input_tokens * TYPESAFE_COST_PER_INPUT_TOKEN
        return {
            "calls": self.usage["calls"],
            "input_tokens": input_tokens,
            "output_tokens": self.usage["output_tokens"],
            "cost_usd": round(cost, 6),
        }


def _simplify(answer):
    kind = answer.get("type")
    if kind == "noul":
        return answer["noul"]
    if kind in ("choice", "score"):
        return answer[kind], answer.get("confidence"), answer.get("probabilities")
    return answer


def load_api_key(env_file):
    """TYPESAFE_API_KEY from the environment first, else from env_file."""
    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key
    if not env_file.exists():
        raise RuntimeError(f"TYPESAFE_API_KEY not set and no .env at {env_file}")
    for line in env_file.read_text().splitlines():
        if line.startswith("TYPESAFE_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"TYPESAFE_API_KEY not found in {env_file}")


def _choice_question(instructions, options):
    return {"type": "choice", "instructions": instructions, "criteria": options}


def _best_match(client, target_desc, candidates):
    """Which of candidates (dict[key, desc]) covers the same ground as target_desc.

    Returns (winner_key, probability), or (None, 0.0) if candidates is empty.
    A single Choice decides among <=255 candidates directly. Above that, this
    runs a tournament: chunk into <=255-option rounds, keep each round's
    winner, and repeat until one Choice can decide among what's left. The
    probability returned is the final round's, not a score against the
    original full field -- an accepted approximation once a field needs more
    than one round.
    """
    round_candidates = dict(candidates)
    while True:
        keys = list(round_candidates)
        if not keys:
            return None, 0.0
        if len(keys) == 1:
            return keys[0], 1.0
        if len(keys) <= CHOICE_MAX_OPTIONS:
            opts = {k: round_candidates[k][:150] for k in keys}
            q = {"same": _choice_question(
                "Which of these notes covers the same ground as the note "
                "being examined, such that keeping both would be redundant?",
                opts)}
            answers = client.ask({"note_under_examination": target_desc}, q)
            pick, _conf, probs = answers["same"]
            return pick, (probs or {}).get(pick, 0.0)
        winners = {}
        for i in range(0, len(keys), CHOICE_MAX_OPTIONS):
            chunk_keys = keys[i:i + CHOICE_MAX_OPTIONS]
            if len(chunk_keys) == 1:
                winners[chunk_keys[0]] = round_candidates[chunk_keys[0]]
                continue
            opts = {k: round_candidates[k][:150] for k in chunk_keys}
            q = {"same": _choice_question(
                "Which of these notes covers the same ground as the note "
                "being examined, such that keeping both would be redundant?",
                opts)}
            answers = client.ask({"note_under_examination": target_desc}, q)
            pick, _conf, _probs = answers["same"]
            winners[pick] = round_candidates[pick]
        round_candidates = winners


def overlap_pairs(memories, client, threshold=0.45):
    """One Choice per memory across all the others' descriptions.

    Returns a list of {"a", "b", "score"} dicts, sorted by score descending,
    for pairs scoring at or above threshold.
    """
    pairs = {}
    for m in memories:
        if not m["desc"]:
            continue
        others = {
            o["key"]: o["desc"] for o in memories
            if o["key"] != m["key"] and o["desc"]
        }
        if len(others) < 2:
            continue
        try:
            pick, prob = _best_match(client, m["desc"], others)
        except RuntimeError:
            continue
        if pick is None:
            continue
        if prob >= threshold:
            key = tuple(sorted((m["key"], pick)))
            pairs[key] = max(pairs.get(key, 0.0), prob)
    ranked = sorted(pairs.items(), key=lambda kv: -kv[1])
    return [{"a": a, "b": b, "score": round(score, 4)} for (a, b), score in ranked]


def default_env_file():
    """<repo-root>/.env, computed relative to this file, not hardcoded."""
    return Path(__file__).resolve().parent.parent / ".env"


def build_report(memories, dead_links, dead_paths, overlap):
    lines = [f"{len(memories)} memories\n"]
    lines.append(f"=== dead [[links]]: {len(dead_links)} ===")
    for d in dead_links:
        lines.append(f"  {d['memory']}  ->  [[{d['link']}]]")
    lines.append(f"\n=== cited paths that no longer exist: {len(dead_paths)} ===")
    lines.append(
        "    (only ~/ and /home/-rooted paths in backticks are checked -- "
        "see the module docstring)"
    )
    for d in dead_paths:
        lines.append(f"  {d['memory']}  ->  {d['path']}")
    if overlap is not None:
        pairs = overlap["pairs"]
        lines.append(f"\n=== overlap pass: {len(pairs)} pairs at or above threshold ===")
        for p in pairs[:20]:
            lines.append(f"  {p['score']:.2f}  {p['a']}\n        {p['b']}")
        usage = overlap["usage"]
        lines.append(
            f"\n{usage['calls']} calls, {usage['input_tokens']} input tokens, "
            f"${usage['cost_usd']:.6f}"
        )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--quick", action="store_true",
        help="structural pass only -- no model, no API call, no cost",
    )
    ap.add_argument(
        "--memory-dir", type=Path, default=None,
        help="memory store directory to check (default: the live store)",
    )
    ap.add_argument(
        "--env-file", type=Path, default=None,
        help="path to a .env file holding TYPESAFE_API_KEY (default: "
             "<repo-root>/.env; a TYPESAFE_API_KEY already in the "
             "environment always takes priority over either)",
    )
    ap.add_argument(
        "--overlap-threshold", type=float, default=0.45,
        help="minimum probability to report an overlap pair (default: 0.45)",
    )
    ap.add_argument(
        "--json", action="store_true",
        help="emit the result as JSON instead of the text report",
    )
    args = ap.parse_args(argv)

    memory_dir = args.memory_dir or LIVE_MEMORY_DIR
    if not memory_dir.is_dir():
        print(f"ERROR: memory dir not found: {memory_dir}", file=sys.stderr)
        return 2

    memories = load_memories(memory_dir)
    dead_links = find_dead_links(memories)
    dead_paths = find_dead_paths(memories)

    overlap = None
    if not args.quick:
        env_file = args.env_file or default_env_file()
        try:
            api_key = load_api_key(env_file)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        client = TypeSafeClient(api_key)
        pairs = overlap_pairs(memories, client, threshold=args.overlap_threshold)
        overlap = {"pairs": pairs, "usage": client.cost_summary()}

    if args.json:
        result = {
            "memory_count": len(memories),
            "dead_links": dead_links,
            "dead_paths": dead_paths,
            "overlap": overlap,
        }
        print(json.dumps(result, indent=2))
    else:
        print(build_report(memories, dead_links, dead_paths, overlap))

    return 1 if (dead_links or dead_paths) else 0


if __name__ == "__main__":
    sys.exit(main())
