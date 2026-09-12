#!/usr/bin/env python3
"""Refuse a git commit whose message is exposed to shell substitution.

Twice in one session a commit message written as `git commit -m "... `idle` ..."`
had a word eaten: the shell ran the backticked text as a command and pasted its
output into the permanent record. The first time it removed the subject of a
sentence from a message that was already pushed. The second time it happened
after I had written the lesson down.

A rule I have to remember is exactly the mitigation this repo has learned not to
trust. Patrick, on being shown the second one: "as long as it never fucking
happens again, we're good." That is a promise a guard can keep and a habit
cannot, so this is a guard.

Refused: any `git commit -m` / `-am` whose message contains a backtick or `$(`
inside double quotes, where the shell WILL substitute before git ever sees it.

Allowed: `git commit -F <file>`, a heredoc, or single quotes -- all three pass
the bytes through untouched. The fix is not "escape it carefully", it is "stop
handing prose to the shell".

Exit 2 blocks the call and shows the message to the agent.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import commit_tokens  # noqa: E402


def message_args(command):
    """The -m/-am message operands in a git commit invocation, with their quoting.

    Returns [(quote_char, text)]. Deliberately a scan rather than a shell parse:
    a parser that got this wrong would fail open, and the whole point is that
    this cannot fail open.
    """
    out = []
    for m in re.finditer(r'-(?:m|am|-message=?)\s*(["\'])(.*?)(?<!\\)\1',
                         command, re.S):
        out.append((m.group(1), m.group(2)))
    return out


def hazards(quote, text):
    """What the shell would substitute in this message before git saw it."""
    if quote == "'":
        return []  # single quotes are literal; nothing expands
    found = []
    if "`" in text:
        found.append("a backtick, which runs the enclosed text as a command")
    if "$(" in text:
        found.append("$( ), which runs the enclosed text as a command")
    return found


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    # CH-237.5 (Grace F10). This was `if "git commit" not in command` -- a
    # literal substring with exactly one space. Bash does not care how much
    # whitespace separates the words, so the guard did not see these:
    #
    #     rc=2  git commit -m "x: $(whoami)"
    #     rc=0  git  commit -m "x: $(whoami)"      two spaces
    #     rc=0  git<TAB>commit -m "x: $(whoami)"   a tab
    #
    # All three run the same substitution before git sees the message. The
    # docstring above explains this is a regex scan rather than a parser
    # precisely because "a parser that got this wrong would fail open, and the
    # whole point is that this cannot fail open" -- and then the trigger did.
    #
    # commit_tokens identifies a commit properly, which also stops the guard
    # firing on a command that merely names one (`git log --grep commit`).
    if commit_tokens(command) is None:
        return 0

    problems = []
    for quote, text in message_args(command):
        for h in hazards(quote, text):
            problems.append(h)

    if not problems:
        return 0

    print(
        "BLOCKED: this commit message would be rewritten by the shell before "
        "git saw it.\n\n"
        + "".join(f"  - {p}\n" for p in dict.fromkeys(problems))
        + "\nThis has already eaten a word out of two permanent commit "
        "messages.\n\n"
        "Write the message to a file and use -F:\n"
        "    cat > /tmp/msg.txt <<'EOF'\n"
        "    subject line\n"
        "\n"
        "    body, backticks and all, passed through untouched\n"
        "    EOF\n"
        "    git commit -F /tmp/msg.txt\n\n"
        "Single quotes also work if the message contains no apostrophe.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
