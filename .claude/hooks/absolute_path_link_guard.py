#!/usr/bin/env python3
"""Stop hook: block assistant replies containing markdown links to RELATIVE paths.

Patrick's IDE renders markdown links relative to the primary workspace root
(claude-env). Links into companion repos (photo-portfolio, etc.) written as
relative paths therefore resolve to nothing and are not clickable. This guard
forces absolute paths (or http(s)://, #anchor, mailto:) by blocking the Stop
event with a reason, so the model must rewrite the links before the user sees
them.

Input (stdin JSON, Stop hook): { "transcript_path": "...", "stop_hook_active": bool, ... }
Output: prints {"decision":"block","reason":"..."} when relative file links are
found; otherwise prints nothing (exit 0 = allow stop).
"""
import json
import re
import sys

# [text](target ...) — capture the target up to the first whitespace or ')'.
# Handles optional <...> angle-bracket targets and an optional "title".
LINK_RE = re.compile(r'\[[^\]]*\]\(\s*<?([^)\s>]+)')

ALLOWED_PREFIXES = (
    '/', 'http://', 'https://', '#', 'mailto:', 'tel:',
    'data:', 'ftp://', 'ftps://', 'vscode://',
)


def is_relative_file_link(target: str) -> bool:
    """True if target is a relative reference (not absolute / URL / anchor)."""
    t = target.strip()
    if not t:
        return False
    if t.startswith('//'):  # protocol-relative URL
        return False
    if t.lower().startswith(ALLOWED_PREFIXES):
        return False
    return True


def last_assistant_text(transcript_path: str) -> str:
    """Return the concatenated visible text of the final assistant message."""
    try:
        with open(transcript_path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError:
        return ''
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        msg = entry.get('message') if isinstance(entry, dict) else None
        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
            continue
        content = msg.get('content')
        parts = []
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    parts.append(block.get('text', ''))
        if parts:
            return '\n'.join(parts)
    return ''


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0  # never block on malformed hook input
    transcript_path = data.get('transcript_path')
    if not transcript_path:
        return 0
    text = last_assistant_text(transcript_path)
    if not text:
        return 0
    offenders = sorted({
        m.group(1) for m in LINK_RE.finditer(text)
        if is_relative_file_link(m.group(1))
    })
    if offenders:
        reason = (
            "BLOCKED by absolute_path_link_guard: your reply has markdown "
            "link(s) with RELATIVE paths. They do NOT resolve in Patrick's IDE "
            "(workspace root is claude-env), so they're not clickable. Rewrite "
            "EACH as an absolute path (e.g. /home/patrick/projects/<repo>/<file>) "
            "or a full http(s):// URL, then finish:\n  - "
            + "\n  - ".join(offenders)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
