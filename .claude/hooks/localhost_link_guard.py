#!/usr/bin/env python3
"""Stop hook: no localhost link reaches Patrick unless the port registry was read first.

Patrick, 2026-10-20: "I want the hook to smash the agent any time it tries to
pass me a link to localhost without first checking the registry."

The registry is docs/ports.md (CE-2.84): every project's local ports, kept so a
collision is found by looking rather than by something failing. That day the
agent handed Patrick http://localhost:5143/admin, started Azurite on 10000 and
had him register a GitHub redirect URI on 5143, all without reading it. The
ports happened to be right; nothing had checked them.

When the agent finishes a turn (from Patrick's last message to now), this reads
the session transcript. Each piece of the agent's own text that names
localhost, 127.0.0.1 or [::1] with a port must come AFTER a read of
docs/ports.md in the same turn: a Read of the file, or a Bash or Grep call that
names ports.md. Every port named must also be in the registry. Otherwise the
stop is blocked and the reason goes back to the agent, which must answer again.

On a retry after a block (stop_hook_active), only text written after the
latest registry read is judged: text already shown can't be unshown, and
judging it again would trap the session. A retry with no registry read in the
turn is still blocked.

It fails closed (specs/guards.md#hooks-fail-closed): unreadable hook input, an
unreadable transcript, or an unreadable registry when a link is present all
block.

Input (stdin JSON, Stop hook): {"transcript_path": "...", "stop_hook_active": bool, ...}
Output: {"decision": "block", "reason": "..."} on stdout to block; nothing to allow.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY = os.path.join(REPO, "docs", "ports.md")
sys.path.insert(0, os.path.join(REPO, "helpers"))

# localhost:5143, 127.0.0.1:10000, [::1]:5143 -- with or without a scheme.
LINK_RE = re.compile(r"(?i)(?<![\w.-])(localhost|127\.0\.0\.1|\[::1\]):(\d{1,5})(?!\d)")


def block(reason):
    print(json.dumps({"decision": "block", "reason": "BLOCKED by localhost_link_guard: " + reason}))
    return 0


def reads_registry(tool_use):
    """True when this tool call reads docs/ports.md."""
    name = tool_use.get("name")
    args = tool_use.get("input") or {}
    if name == "Read":
        return str(args.get("file_path", "")).endswith("ports.md")
    if name == "Bash":
        return "ports.md" in str(args.get("command", ""))
    if name == "Grep":
        return "ports.md" in str(args.get("path", "")) or "ports.md" in str(args.get("glob", ""))
    return False


def is_patricks_message(entry):
    """A message Patrick sent: a user entry that isn't only tool results or harness metadata."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content)
    return False


def this_turn(path):
    """The entries after Patrick's last message. Raises OSError when unreadable."""
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)
    start = 0
    for i, entry in enumerate(entries):
        if is_patricks_message(entry):
            start = i + 1
    return entries[start:]


def scan(turn):
    """(registry read positions, [(position, [(host, port)])] for text naming localhost ports)."""
    reads, links, pos = [], [], 0
    for entry in turn:
        message = entry.get("message") or {}
        if entry.get("type") != "assistant" or message.get("role") != "assistant":
            continue
        content = message.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        for b in blocks:
            if not isinstance(b, dict):
                continue
            pos += 1
            if b.get("type") == "tool_use" and reads_registry(b):
                reads.append(pos)
            elif b.get("type") == "text":
                found = [(m.group(1).lower(), int(m.group(2))) for m in LINK_RE.finditer(b.get("text", ""))]
                if found:
                    links.append((pos, found))
    return reads, links


def registered_ports():
    """[(start, end)] from the registry. Raises when it can't be read or parsed."""
    from port_lint import parse_ports
    with open(REGISTRY, "r", encoding="utf-8") as fh:
        return [(start, end) for start, end, _ in parse_ports(fh.read())]


def named(found):
    return ", ".join(sorted({f"{host}:{port}" for host, port in found}))


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return block("the hook input couldn't be read, so it can't tell whether this reply links to localhost.")
    path = data.get("transcript_path")
    try:
        turn = this_turn(path) if path else None
    except OSError:
        turn = None
    if turn is None:
        return block(f"the session transcript ({path or 'none given'}) couldn't be read, so it can't tell whether this reply links to localhost.")

    reads, links = scan(turn)
    if not links:
        return 0

    if data.get("stop_hook_active"):
        if not reads:
            judged, unchecked = [], [p for p in links]
        else:
            judged, unchecked = [s for s in links if s[0] > max(reads)], []
    else:
        judged = links
        unchecked = [s for s in links if not any(r < s[0] for r in reads)]

    if unchecked:
        found = [f for _, fs in unchecked for f in fs]
        return block(
            f"your reply gives Patrick a localhost link ({named(found)}) without reading the port "
            f"registry first in this turn. Read {REGISTRY}, confirm the port is the one registered "
            "for the project you're linking, then give the link again.")

    try:
        ranges = registered_ports()
    except Exception as exc:  # fail closed: a link is present and the registry can't be checked
        return block(f"the port registry {REGISTRY} couldn't be read ({type(exc).__name__}), so the link can't be checked.")

    unregistered = [(h, p) for _, fs in judged for h, p in fs if not any(s <= p <= e for s, e in ranges)]
    if unregistered:
        return block(
            f"{named(unregistered)} isn't in the port registry ({REGISTRY}). Don't give Patrick a port the "
            "registry doesn't list: use the project's registered port, or register the port there first "
            "(python3 helpers/port_lint.py docs/ports.md must pass).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
