#!/usr/bin/env python3
"""
agent_model_guard.py -- PreToolUse hook for the Agent and Workflow tools.

Refuses any subagent that would run on an expensive model by default.
Every Agent call must name its model, and every agent() call inside a
Workflow script must carry a literal `model: 'haiku'` or `model: 'sonnet'`.
Opus (or any other model), a fork (forks always inherit the parent's
model), a named or nested workflow whose script this hook cannot read, and
an agent() call whose options it cannot see are all refused -- unless
Patrick's most recent message says "allow opus".

Why (Patrick, 2026-10-08, nfl-stats session): subagents inherit the session
model when none is set, so a whole session of reviews, verifiers and reruns
ran on Opus for work Haiku or Sonnet could do -- after he had already asked
for Haiku and Sonnet. A memory note did not stop it; this does.

Override: the word pair "allow opus" (any case) in Patrick's latest real
message. Tool results, subagent hand-backs and system notifications in the
transcript never count -- only text Patrick typed.

Fails closed: anything this hook cannot parse is refused with the reason.

Input: PreToolUse JSON on stdin. Output: a permissionDecision "deny" JSON on
stdout when refusing; nothing (silent pass) otherwise.
"""
import json
import os
import re
import sys

ALLOWED = ("haiku", "sonnet")
OVERRIDE = re.compile(r"\ballow\s+opus\b", re.IGNORECASE)
# Text that marks a "user" transcript entry as not typed by Patrick.
NOT_PATRICK = ("<agent-message", "[SYSTEM NOTIFICATION", "<task-notification", "[Subagent hand-back]")
AGENT_CALL = re.compile(r"(?<![\w.$])agent\s*\(")
NESTED_WORKFLOW = re.compile(r"(?<![\w.$])workflow\s*\(")
MODEL_KEY = re.compile(r"(?<![\w$])model\s*:\s*$")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "agent_model_guard: " + reason,
    }}))
    sys.exit(0)


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                return None  # a tool_result (or anything else) is not Patrick typing
            parts.append(block.get("text", ""))
        return "\n".join(parts)
    return None


def latest_patrick_message(transcript_path):
    """The text of the most recent transcript entry Patrick typed, or ""."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    latest = ""
    with open(transcript_path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "user" or entry.get("isMeta"):
                continue
            message = entry.get("message") or {}
            if message.get("role") != "user":
                continue
            text = _text_of(message.get("content"))
            if text is None or any(marker in text for marker in NOT_PATRICK):
                continue
            latest = text
    return latest


def scan_call(src, start):
    """From just after an opening '(' at `start`, return (code_view,
    literals) for the call's arguments: code_view has every string
    literal's contents blanked (so text inside a prompt can never look like
    an option), literals maps each literal's opening offset (in code_view)
    to its original contents. None if the call never closes."""
    depth, i, n = 1, start, len(src)
    view, literals = [], {}
    stack = []  # string/template context: "'", '"', '`', '${', '{'
    lit_start = None
    lit_chars = []
    while i < n:
        c = src[i]
        top = stack[-1] if stack else None
        if top in ("'", '"'):
            if c == "\\":
                lit_chars.append(src[i:i + 2]); view.append("  "); i += 2; continue
            if c == top:
                stack.pop(); literals[lit_start] = "".join(lit_chars); view.append(c)
            else:
                lit_chars.append(c); view.append(" ")
            i += 1; continue
        if top == "`":
            if c == "\\":
                view.append("  "); i += 2; continue
            if c == "`":
                stack.pop(); view.append(c); i += 1; continue
            if c == "$" and src[i + 1:i + 2] == "{":
                stack.append("${"); view.append("  "); i += 2; continue
            view.append(" "); i += 1; continue
        # code: top level, or inside a template ${ ... } expression
        if c in ("'", '"', "`"):
            stack.append(c); view.append(c)
            if c != "`":
                lit_start, lit_chars = len("".join(view)) - 1, []
            i += 1; continue
        if c == "/" and src[i + 1:i + 2] == "/":
            end = src.find("\n", i); end = n if end < 0 else end
            view.append(" " * (end - i)); i = end; continue
        if c == "/" and src[i + 1:i + 2] == "*":
            end = src.find("*/", i + 2); end = n if end < 0 else end + 2
            view.append(" " * (end - i)); i = end; continue
        if top in ("${", "{"):
            if c == "{":
                stack.append("{")
            elif c == "}":
                stack.pop()
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return "".join(view), literals
        view.append(c); i += 1
    return None


def agent_models(script):
    """For each agent( call in a workflow script: the literal model it
    names, or None when it names none the hook can see."""
    out = []
    for match in AGENT_CALL.finditer(script):
        scanned = scan_call(script, match.end())
        if scanned is None:
            raise ValueError(f"an agent( call at offset {match.start()} never closes")
        view, literals = scanned
        model = None
        for pos, char in enumerate(view):
            if char in ("'", '"') and pos in literals and MODEL_KEY.search(view[:pos]):
                model = literals[pos]
        out.append((match.start(), model))
    return out


def check_agent(tool_input, allow_opus):
    if tool_input.get("subagent_type") == "fork":
        if allow_opus:
            return None
        return ("a fork always runs on the parent's model. Use a named agent with "
                "model 'haiku' or 'sonnet', or get Patrick's \"allow opus\".")
    model = tool_input.get("model")
    if not model:
        return ("set the Agent `model` explicitly -- 'haiku' for mechanical checks, "
                "'sonnet' for reviews. Without it the agent inherits the session's model.")
    if model not in ALLOWED and not allow_opus:
        return (f"model '{model}' needs Patrick's \"allow opus\" in his latest message. "
                "Use 'haiku' or 'sonnet'.")
    return None


def check_workflow(tool_input, allow_opus):
    script = tool_input.get("script")
    path = tool_input.get("scriptPath")
    if not script and path:
        with open(path, encoding="utf-8") as handle:
            script = handle.read()
    if not script:
        if allow_opus:
            return None
        return ("a workflow run by name can't be checked for agent models. Pass the "
                "script (or scriptPath), with model 'haiku' or 'sonnet' on every agent().")
    if NESTED_WORKFLOW.search(script) and not allow_opus:
        return ("a nested workflow() call can't be checked for agent models; inline its "
                "agents with explicit models instead.")
    calls = agent_models(script)
    line_of = lambda offset: script.count("\n", 0, offset) + 1
    missing = [line_of(o) for o, m in calls if m is None]
    if missing:
        return ("every agent() call needs a literal `model: 'haiku'` or `model: 'sonnet'` "
                "in its options -- missing at script line(s) " + ", ".join(map(str, missing)) + ".")
    pricey = [(line_of(o), m) for o, m in calls if m not in ALLOWED]
    if pricey and not allow_opus:
        return ("model " + ", ".join(f"'{m}' (line {l})" for l, m in pricey)
                + " needs Patrick's \"allow opus\" in his latest message.")
    return None


def main():
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name")
    if tool not in ("Agent", "Workflow"):
        return
    tool_input = payload.get("tool_input") or {}
    allow_opus = bool(OVERRIDE.search(latest_patrick_message(payload.get("transcript_path"))))
    reason = (check_agent if tool == "Agent" else check_workflow)(tool_input, allow_opus)
    if reason:
        deny(reason)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:  # fail closed
        deny(f"could not check this call ({type(error).__name__}: {error}); refusing.")
