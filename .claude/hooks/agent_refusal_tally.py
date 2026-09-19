#!/usr/bin/env python3
"""
agent_refusal_tally.py — PostToolUse hook for the Agent tool.

CE-12.15. When a subagent finishes, the refusals it hit are printed to
whoever dispatched it, read from its OWN transcript rather than trusted from
its final report. Measured on 2026-09-17 by hand-auditing three transcripts
against their own final reports: one report opened "No refusals" and then
described two, while its transcript held six; one described a single
refusal and omitted an earlier one it had worked around. Agent reports
understate refusals, so nothing here depends on the report at all.

WHERE THE DATA COMES FROM
A completed (synchronous) Agent tool call hands this hook, in `tool_response`,
the same object Claude Code itself later persists as that call's
`toolUseResult` — a dict with `status: "completed"` and an `agentId`. That
subagent's own transcript lives at a sibling path Claude Code does not hand
us directly (only a SubagentStop hook gets `agent_transcript_path`), but the
naming convention is fixed and used elsewhere in this harness
(_observed.py, claude-harness): `<dirname(transcript_path)>/<session_id>/
subagents/agent-<agentId>.jsonl`.

An Agent call whose `tool_response` is not a completed-with-agentId dict —
the call itself was denied before any subagent ran, or it is a
`status: "async_launched"` background dispatch that has not finished yet —
has no "finished subagent" to inspect. This hook is silent in that case;
`status: "async_launched"` is a job for a SubagentStop hook, not this one.

WHAT COUNTS AS A DENIAL
Reading real transcripts (2026-09-18, Claude Code 2.1.x, under
~/.claude/projects/*/subagents/) turned up denials showing up as an
`is_error: true` tool_result in exactly two shapes, never as a structured
`permissionDecision` field — Claude Code does not persist that field in the
transcript, only its rendered consequence:
  * a bare `permissionDecision: "deny"` with no reason renders as
    "Hook PreToolUse:<Tool> denied this tool";
  * a bare deny WITH a reason renders as that reason directly, which in this
    repo's guards always starts "BLOCKED: ...";
  * a hook that exits non-zero (crashes, or a plain hard block written as a
    raised error rather than a JSON deny) renders as
    "PreToolUse:<Tool> hook error: [<cmd>]: <the hook's stderr>" — and that
    stderr, again, usually starts "BLOCKED: ...".
A human declining a permission dialog renders as "The user doesn't want to
proceed..." — no BLOCKED/hook-error/denied-this-tool text, so it is not
matched here. This hook counts guard refusals, not human declines.

BOUNDED READ
At most MAX_TRANSCRIPT_LINES lines of the subagent's transcript are parsed.
A transcript longer than that is truncated silently past the bound — any
denial recorded after line MAX_TRANSCRIPT_LINES is not counted. This keeps
one huge subagent run (a transcript can be large enough that reading it
directly is explicitly discouraged elsewhere in this harness) from making
every dispatch pay an unbounded read.

CONSTRAINTS
Read-only: never writes anything, never changes any decision, always exits
0. Output is for the dispatcher: one line per refusal, naming the tool, the
first line of the refusal, and the first 120 characters of the command or
path that triggered it.
"""
import json
import os
import re
import sys

MAX_TRANSCRIPT_LINES = 20000

# Matches "PreToolUse:Bash hook error:" / "PreToolUse:Write hook error:" and
# "Hook PreToolUse:Bash denied this tool" alike, capturing the tool name.
_DENIAL_RE = re.compile(
    r"^(?:Hook )?[A-Za-z]+:([A-Za-z]+)(?: hook error:| denied this tool)"
)

# Preference order for which tool_input field is "the command or path that
# caused it" — the first one present wins. Falls back to a compact rendering
# of whatever input there is, since a tool this hook has never seen still
# deserves *something* rather than a blank.
_COMMAND_KEYS = ("command", "file_path", "path", "pattern", "url", "query", "prompt")


def _refusal_tool_from_text(text):
    """The tool name embedded in the refusal text itself, or None."""
    m = _DENIAL_RE.match(text or "")
    return m.group(1) if m else None


def _looks_like_refusal(text):
    """Is this is_error tool_result text a guard's refusal (not e.g. a human
    decline, which never carries any of these markers)?"""
    if not text:
        return False
    if text.startswith("BLOCKED"):
        return True
    return _refusal_tool_from_text(text) is not None


def _tool_result_text(content):
    """Normalize a tool_result's `content` (str, or a list of content
    blocks) down to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p)
    return ""


def _command_or_path(tool_input):
    if not isinstance(tool_input, dict):
        return ""
    for key in _COMMAND_KEYS:
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    if tool_input:
        try:
            return json.dumps(tool_input, sort_keys=True)
        except (TypeError, ValueError):
            return str(tool_input)
    return ""


def _load_denials(path):
    """Every denial found in the subagent transcript at `path`, as
    (tool_name, refusal_text, command_or_path) tuples, in transcript order.

    Raises OSError if `path` cannot be opened — the caller distinguishes
    "could not read the transcript at all" from "read it, found nothing".
    """
    denials = []
    tool_use_map = {}  # tool_use_id -> (tool_name, tool_input)

    with open(path, encoding="utf-8") as fh:
        for i, raw_line in enumerate(fh):
            if i >= MAX_TRANSCRIPT_LINES:
                break
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            if record.get("type") == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        block_input = block.get("input")
                        tool_use_map[block.get("id")] = (
                            block.get("name"),
                            block_input if isinstance(block_input, dict) else {},
                        )
            elif record.get("type") == "user":
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    if not block.get("is_error"):
                        continue
                    text = _tool_result_text(block.get("content"))
                    if not _looks_like_refusal(text):
                        continue
                    tool_name, tool_input = tool_use_map.get(
                        block.get("tool_use_id"), (None, {})
                    )
                    if not tool_name:
                        tool_name = _refusal_tool_from_text(text) or "unknown"
                    denials.append((tool_name, text, _command_or_path(tool_input)))

    return denials


def _emit(context):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    }))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(payload, dict):
        return

    tool_response = payload.get("tool_response")
    if not isinstance(tool_response, dict):
        return  # the Agent call itself was denied, or gave no result to read.
    if tool_response.get("status") != "completed":
        return  # not a finished synchronous agent -- nothing to tally yet.

    agent_id = tool_response.get("agentId")
    if not agent_id:
        return

    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id")
    if not transcript_path or not session_id:
        return

    subagent_path = os.path.join(
        os.path.dirname(transcript_path), session_id, "subagents",
        f"agent-{agent_id}.jsonl",
    )

    try:
        denials = _load_denials(subagent_path)
    except OSError as exc:
        _emit(
            f"SUBAGENT REFUSAL TALLY: agent {agent_id}'s transcript could not "
            f"be read at {subagent_path} ({exc.strerror or exc})."
        )
        return

    if not denials:
        _emit(
            f"SUBAGENT REFUSAL TALLY: no refusals were found in agent "
            f"{agent_id}'s transcript ({subagent_path})."
        )
        return

    lines = [
        f"SUBAGENT REFUSAL TALLY: {len(denials)} refusal(s) in agent "
        f"{agent_id}'s transcript ({subagent_path}):"
    ]
    for n, (tool_name, text, cmd) in enumerate(denials, 1):
        first_line = text.split("\n", 1)[0].strip()
        lines.append(f"  {n}. {tool_name}: {first_line} — {cmd[:120]}")
    _emit("\n".join(lines))


if __name__ == "__main__":
    main()
