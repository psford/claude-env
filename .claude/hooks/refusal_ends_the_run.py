#!/usr/bin/env python3
"""refusal_ends_the_run.py — PreToolUse hook, all tools.

CE-12.14. Patrick, 2026-09-17, after reading what two dev lanes did on the
same day: "the strictures will only tighten from here."

WHAT HAPPENED
Both lanes carried a brief saying, in these words, that a refusal ends the
run and is reported verbatim. Both ignored it, in the tool call immediately
after the deny: one wrote a script whose own docstring says it runs the
refused steps "only via subprocess" so that no command is typed into a
shell directly; the other imported a guard's source under `python3 -c` to
probe it, then retyped the refused message without backticks and split the
command in two. Three reports that day also understated their refusals.

The words did not bind. This makes it mechanical: a subagent that has been
refused once gets no further tool calls. It may still write its report and
stop — nothing here touches assistant text, only tool calls.

DESIGN
Acts only when the payload carries an `agent_id` — it governs subagents and
leaves the main session alone. It reads that agent's OWN transcript,
`<dirname(transcript_path)>/<session_id>/subagents/agent-<agent_id>.jsonl`
(the parent's transcript_path plus session_id locates it; the subagent's
own record is never in transcript_path itself — see
reference_hook_input_subagent_identity), and looks for an earlier tool
result that was a denial:
  - a PreToolUse permissionDecision "deny" (recorded in the transcript as
    the hook's permissionDecisionReason text, is_error true — by convention
    in this repo that text starts with "BLOCKED"); or
  - an error tool_result carrying a guard's refusal text emitted through
    the plain exit-2 protocol, which Claude Code wraps as
    "PreToolUse:<Tool> hook error: [<command>]: <text>".

If it finds one, it denies THIS call, naming the earlier refused command
(correlated back to the assistant's tool_use block by tool_use_id) and the
first line of that refusal, and telling the agent to write its report and
stop. It names no way to clear the state, because there is none — the
dispatcher re-dispatches if the block was wrong.

No agent_id, or no earlier denial found, and it is silent: exit 0, no
output. Untouched, not "allowed with a note" — a note on every ordinary
call would bury the one that matters.

CONSTRAINTS
- Read-only over the transcript. Writes no state of its own.
- A transcript that cannot be located or read is reported via
  additionalContext and the call is ALLOWED — a missing file must not
  silently gag every agent.
- Bounded read: at most MAX_LINES lines of the transcript are scanned, so
  one call cannot be slowed by an unbounded file. Denials are rare and the
  earliest one is the one that matters, so the scan reads forward from the
  start of the file and stops at the first match (or the bound).
"""
import json
import re
import sys
from pathlib import Path

ALLOW = 0
BLOCK = 2

# The scan reads at most this many JSONL lines before giving up and treating
# the transcript as having no denial. Subagent transcripts in this repo run
# to a few thousand lines at most; this bound exists so a pathological or
# runaway transcript cannot make an ordinary tool call noticeably slower.
MAX_LINES = 20000

# The two textual shapes a denial takes once Claude Code has recorded it in
# a transcript (measured against real subagent transcripts under
# ~/.claude/projects/*/subagents/ — see the brief for CE-12.14). Anchored to
# the start of the text so an unrelated tool output that happens to mention
# these words mid-sentence does not match.
DENIAL_PATTERNS = (
    re.compile(r'^PreToolUse:\S+ hook error:'),
    re.compile(r'^BLOCKED\b'),
)

# Fields worth quoting when describing the refused tool call. Checked in
# order; the first one present wins.
DESCRIBE_KEYS = ("command", "file_path", "path", "pattern", "url", "prompt", "query")


def describe_tool_use(name, tool_input):
    name = name or "(unknown tool)"
    if isinstance(tool_input, dict):
        for key in DESCRIBE_KEYS:
            value = tool_input.get(key)
            if value:
                return f"{name}: {value}"
    return name


def first_line(text):
    return text.split("\n", 1)[0].strip()


def extract_text(content):
    """tool_result content is either a plain string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts)
    return ""


def is_denial_text(text):
    if not isinstance(text, str) or not text:
        return False
    return any(p.match(text) for p in DENIAL_PATTERNS)


def find_earlier_denial(transcript_path):
    """Scan the transcript for the FIRST denied tool_result.

    Returns (command_description, refusal_first_line) or None. Read-only;
    never writes to the transcript or anywhere else. Raises OSError if the
    file cannot be opened — the caller decides what "unreadable" means.
    """
    tool_uses = {}  # tool_use_id -> (tool_name, tool_input)
    with open(transcript_path, encoding="utf-8") as fh:
        for i, raw in enumerate(fh):
            if i >= MAX_LINES:
                break
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            msg = entry.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue

            if msg.get("role") == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses[block.get("id")] = (
                            block.get("name"), block.get("input"),
                        )
                continue

            if msg.get("role") != "user":
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                if not block.get("is_error"):
                    continue
                text = extract_text(block.get("content"))
                if not is_denial_text(text):
                    continue
                tool_name, tool_input = tool_uses.get(block.get("tool_use_id"), (None, None))
                return describe_tool_use(tool_name, tool_input), first_line(text)
    return None


def allow_with_note(note):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": note,
        }
    }))
    return ALLOW


def deny(command_desc, refusal_line):
    reason = (
        "BLOCKED by refusal_ends_the_run: this agent was already refused "
        "once, and a refusal ends the run.\n\n"
        f"Earlier refused call: {command_desc}\n"
        f"Its refusal: {refusal_line}\n\n"
        "Write your report now, disclose that refusal in it, and stop. "
        "There is no way to clear this state -- the dispatcher re-dispatches "
        "if the block was wrong."
    )
    # Both protocols: the JSON decision for a normal PreToolUse read, and a
    # plain-text refusal on stderr for the `claude -p` subprocess case where
    # JSON-only output is easy to miss (measured elsewhere in this repo).
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    print(reason, file=sys.stderr)
    return BLOCK


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return ALLOW
    if not isinstance(payload, dict):
        return ALLOW

    agent_id = payload.get("agent_id")
    if not agent_id:
        return ALLOW  # Main session. Untouched.

    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id")
    if not transcript_path or not session_id:
        return allow_with_note(
            "refusal_ends_the_run: payload has an agent_id but no "
            "transcript_path/session_id to locate its transcript -- "
            "allowing rather than gagging every agent on a payload shape "
            "this hook cannot read."
        )

    subagent_transcript = (
        Path(transcript_path).parent / session_id / "subagents" / f"agent-{agent_id}.jsonl"
    )

    try:
        found = find_earlier_denial(subagent_transcript)
    except OSError as exc:
        return allow_with_note(
            f"refusal_ends_the_run: could not read {subagent_transcript} "
            f"({exc}) -- allowing rather than gagging every agent on a "
            "missing or unreadable transcript."
        )

    if found is None:
        return ALLOW  # No earlier denial. Untouched.

    command_desc, refusal_line = found
    return deny(command_desc, refusal_line)


if __name__ == "__main__":
    sys.exit(main())
