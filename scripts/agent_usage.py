#!/usr/bin/env python3
"""
agent_usage.py -- what each subagent in a Claude Code session used and cost.

Reads a session's logs (~/.claude/projects/<project>/<session>/subagents/,
Agent-tool agents and workflow agents) and prints one row per subagent:
when it started, its model, its label, the requests it made, its tokens
(input, cache write, cache read, output) and its cost at API list prices,
then totals by model. Built 2026-10-08 so subagent model choice and context
size can be checked from the logs instead of taken on trust.

Usage:
  agent_usage.py                      the most recent session with subagents
  agent_usage.py <session-id | path>  a specific session (id, its folder, or its .jsonl)
  agent_usage.py --since 2026-10-08T00:17:10Z   only subagents started at or after this time
  agent_usage.py --json               machine-readable output

Notes:
- One API response can span several log lines with repeated usage; each
  response is counted once, with the largest usage any of its lines records.
- The logs often keep only an early streaming snapshot of output_tokens, and
  extended-thinking text is not kept at all, so OUTPUT (and so cost) is a
  floor. The "visible out" column estimates the text the agent actually wrote
  (characters / 4) as a second floor.
- Main-conversation tokens are not counted -- subagents only.
"""
import argparse
import glob
import json
import os
import sys

# USD per million tokens. Source: https://platform.claude.com/docs/en/about-claude/pricing
# (fetched 2026-10-08). Haiku 5.5's short-prompt tier (<= 100k-token prompt).
PRICES = {
    "opus": {"in": 4.00, "w5": 5.00, "w1h": 8.00, "read": 0.20, "out": 20.00},
    "sonnet": {"in": 2.00, "w5": 2.50, "w1h": 4.00, "read": 0.10, "out": 10.00},
    "haiku": {"in": 0.10, "w5": 0.125, "w1h": 0.20, "read": 0.01, "out": 0.50},
}
FIELDS = ("in", "w5", "w1h", "read", "out")
PROJECTS = os.path.expanduser("~/.claude/projects")


def family(model):
    for name in PRICES:
        if name in (model or ""):
            return name
    return None


def find_session(arg):
    """The session folder (the one holding subagents/) for an id, folder or .jsonl."""
    if arg:
        if arg.endswith(".jsonl"):
            arg = arg[:-6]
        if os.path.isdir(os.path.join(arg, "subagents")):
            return arg
        hits = glob.glob(os.path.join(PROJECTS, "*", arg))
        hits = [h for h in hits if os.path.isdir(os.path.join(h, "subagents"))]
        if not hits:
            sys.exit(f"no session with subagents found for {arg!r}")
        return hits[0]
    dirs = [d for d in glob.glob(os.path.join(PROJECTS, "*", "*")) if os.path.isdir(os.path.join(d, "subagents"))]
    if not dirs:
        sys.exit("no session with subagents found")
    return max(dirs, key=lambda d: os.path.getmtime(os.path.join(d, "subagents")))


def label_of(path):
    meta = path[:-6] + ".meta.json"
    try:
        with open(meta, encoding="utf-8") as handle:
            m = json.load(handle)
        return m.get("description") or m.get("label") or m.get("agentType") or ""
    except (OSError, ValueError):
        return ""


def agent_usage(path):
    """(start time, models, requests, token totals, visible output chars) for one transcript."""
    start, models, requests, chars = None, set(), {}, 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            stamp = entry.get("timestamp")
            if stamp and (start is None or stamp < start):
                start = stamp
            message = entry.get("message") or {}
            if entry.get("type") != "assistant" or not message.get("usage"):
                continue
            model = message.get("model") or ""
            models.add(model)
            usage = message["usage"]
            cache = usage.get("cache_creation") or {}
            seen = requests.setdefault(message.get("id") or id(entry), {"model": model, **{f: 0 for f in FIELDS}})
            for field, value in (
                ("in", usage.get("input_tokens", 0)),
                ("w5", cache.get("ephemeral_5m_input_tokens", usage.get("cache_creation_input_tokens", 0))),
                ("w1h", cache.get("ephemeral_1h_input_tokens", 0)),
                ("read", usage.get("cache_read_input_tokens", 0)),
                ("out", usage.get("output_tokens", 0)),
            ):
                seen[field] = max(seen[field], value or 0)
            for block in message.get("content") or []:
                if block.get("type") == "text":
                    chars += len(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    chars += len(json.dumps(block.get("input", {})))
    return start, models, requests, chars


def cost(tokens, fam):
    price = PRICES.get(fam)
    if price is None:
        return None
    return sum(tokens[f] * price[f] for f in FIELDS) / 1e6


def collect(session, since=None):
    rows = []
    paths = glob.glob(os.path.join(session, "subagents", "agent-*.jsonl"))
    paths += glob.glob(os.path.join(session, "subagents", "workflows", "*", "agent-*.jsonl"))
    for path in paths:
        start, models, requests, chars = agent_usage(path)
        if not requests or (since and (start or "") < since):
            continue
        tokens = {f: sum(r[f] for r in requests.values()) for f in FIELDS}
        fams = sorted({family(m) or m for m in models})
        fam = fams[0] if len(fams) == 1 else "mixed"
        dollars = sum(cost({f: r[f] for f in FIELDS}, family(r["model"])) or 0 for r in requests.values())
        workflow = os.path.basename(os.path.dirname(path)) if "/workflows/" in path else ""
        rows.append({"start": start, "model": fam, "label": label_of(path), "workflow": workflow,
                     "requests": len(requests), **tokens, "visible_out_est": chars // 4, "cost": dollars})
    return sorted(rows, key=lambda r: r["start"] or "")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("session", nargs="?")
    parser.add_argument("--since")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    session = find_session(args.session)
    rows = collect(session, args.since)
    if args.json:
        print(json.dumps({"session": session, "since": args.since, "subagents": rows}, indent=1))
        return
    print(f"session {session}" + (f", since {args.since}" if args.since else ""))
    print(f"{'start (UTC)':20} {'model':7} {'reqs':>5} {'cache write':>12} {'cache read':>12} {'output':>9} {'visible out':>12} {'cost $':>8}  label")
    for r in rows:
        print(f"{(r['start'] or '')[:19]:20} {r['model']:7} {r['requests']:5} {r['w5'] + r['w1h']:12,} {r['read']:12,} "
              f"{r['out']:9,} {r['visible_out_est']:12,} {r['cost']:8.2f}  {(r['workflow'] + ' ' if r['workflow'] else '') + r['label'][:60]}")
    print("\nby model:")
    for fam in sorted({r["model"] for r in rows}):
        sel = [r for r in rows if r["model"] == fam]
        print(f"  {fam:7} {len(sel):4} agents  {sum(r['requests'] for r in sel):6} requests  "
              f"{sum(r['w5'] + r['w1h'] for r in sel):>12,} cache write  {sum(r['read'] for r in sel):>13,} cache read  "
              f"${sum(r['cost'] for r in sel):.2f}")
    print(f"  total   {len(rows):4} agents  ${sum(r['cost'] for r in rows):.2f}  (output is a floor; see --help)")


if __name__ == "__main__":
    main()
