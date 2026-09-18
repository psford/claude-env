#!/usr/bin/env python3
"""Which repository is this hook actually about?

A hook process inherits the session's working directory. In a multi-repo
workspace that is routinely a *different* repository from the one the command
touches, so a hook that runs `git diff --cached` inspects the wrong index and
finds nothing. It does not fail loudly -- it passes, vacuously, which is worse.

Found on 2026-08-08 after main_branch_guard blocked every commit in every repo
because the session sat in claude-env on main. That was the loud symptom;
audit found 31 hooks with the same defect, most of them silent.

Usage in a hook, immediately after reading the payload:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _repo_context import enter_target_repo

    enter_target_repo(hook_input)

After that call, bare `subprocess.run(["git", ...])` inherits the right
directory and every existing call site is correct without being rewritten.
"""

import os
import re
import shlex
import subprocess

# `&` sits in the class, and `&&` stays FIRST in the alternation: a bare `&`
# backgrounds one command and starts another (CH-237.10), so
# `: & cd ios && git push` is three statements -- the push runs from ios, and
# a splitter that keeps `: & cd ios` whole hands every guard tokens[0] == ":"
# and the cd is never tracked.
STATEMENT_SPLIT = re.compile(r'&&|\|\||[;\n|&]')
GIT_INVOCATION = re.compile(
    r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:sudo\s+)?(?:\S*/)?git\b')
QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')
# bash DELETES a backslash-newline before it parses anything -- it does not
# replace it with a space. The difference matters: `res\<newline>et` rejoins as
# `reset`, so substituting a space would split a keyword back apart and hand the
# guard a string bash never sees.
CONTINUATION = re.compile(r'\\\n')
# A shell's "run this string" flag is a single-dash cluster containing `c`.
# `-c`, `-lc`, `-cl`, `-ic` are one instruction to bash, and matching a single
# spelling is how two sibling parsers ended up with two opposite one-character
# bugs (CH-237.4, Grace F5): claude-env tested `"-c" in tokens`, so `bash -lc`
# walked `git reset --hard` past every guard there; the harness tested
# `token.endswith("c")`, so `bash -cl` walked every reserved ticket command --
# including Patrick's UAT verdict -- past this one.
#
# A long option does not match: `--rcfile` has a second dash, which is not in
# the character class.
COMMAND_FLAG = re.compile(r'-[A-Za-z]*c[A-Za-z]*')

# The options that consume the token after them. A scan that does not skip
# their value reads that value as the command -- or, worse, stops there.
#
# The short ones were missed on the first pass and QA found it (CH-237.4). The
# harness guard walks tokens positionally and gives up at the first bare word,
# so `extglob` ended the scan before `-c` was ever reached:
#
#     rc=0   bash -o posix   -c 'ticket uat CH-1 --verdict accepted'
#     rc=0   bash -O extglob -c 'ticket uat CH-1 --verdict accepted'
#     rc=0   bash +O extglob -c 'ticket uat CH-1 --verdict accepted'
#     rc=2   bash -c / -lc / -cl / -ic / --rcfile f -c
#
# Those are real invocations -- bash runs the payload -- and `cmd_uat` has no
# actor check of its own, so this guard is the only thing in front of a forged
# UAT verdict. Which is the same hole this ticket opened by, one option over.
#
# `+o` and `+O` are here because bash accepts a leading plus for both, and a
# tuple that lists only the minus spellings is the `-c` mistake again.
FLAGS_TAKING_A_VALUE = ("--rcfile", "--init-file", "-o", "-O", "+o", "+O")


def is_command_flag(token):
    """True when `token` tells a shell that an argument is a command to run."""
    return bool(COMMAND_FLAG.fullmatch(token))


def statements(command):
    """Split into commands, ignoring separators inside quotes.

    `python3 -c "import json; ..."` is one statement. Splitting at the ';'
    inside the string produces two fragments, neither of which looks like what
    it is.

    Line continuations are joined first, because bash joins them before it parses
    anything. Without that, a git invocation split over two lines by a trailing
    backslash becomes two halves, neither of which looks like a commit -- which
    permitted both a commit onto main and a destructive reset past the guards
    that exist to refuse them. Fixing it here fixes it for every caller rather
    than for one regex.
    """
    command = CONTINUATION.sub("", command)
    masked = QUOTED.sub(lambda m: " " * len(m.group()), command)
    start = 0
    for match in STATEMENT_SPLIT.finditer(masked):
        chunk = command[start:match.start()].strip()
        if chunk:
            yield chunk
        start = match.end()
    tail = command[start:].strip()
    if tail:
        yield tail


HEREDOC_START = re.compile(r'<<-?\s*(["\']?)([A-Za-z_][A-Za-z0-9_]*)\1')
FEEDS_CODE = re.compile(
    r'^\s*(?:\S*/)?(?:bash|sh|zsh|python3?|perl|ruby|node)\b')


def strip_heredoc_bodies(command, scan_interpreter_bodies=True):
    """Drop heredoc bodies before scanning. They are data, not commands.

    `scan_interpreter_bodies=False` drops them ALL, including the ones fed to
    python/bash. Use it when the guard's subject is SHELL SYNTAX rather than
    what a command does: `2>/dev/null` inside python source is a string, not a
    redirect. stderr_suppression_guard blocked three legitimate commands in ten
    minutes on 2026-08-09 -- once via `-c`, twice via `python3 - <<PY` -- each
    time reading its own repair script as a suppression.

    The default stays True: for guards about what a command DOES, an
    interpreter heredoc genuinely is code and must be read.

    Statements are split on newlines, so every line of a heredoc becomes a
    candidate command. On 2026-08-08 that made a sentence describing a store
    path -- `scan for <root>/*/.claude/tickets/config.json` -- match the
    shell-redirect pattern, because the `>` closing `<root>` sits in front of a
    store path. The prose was blocked; nothing was writing anywhere near the
    store.

    The command line itself is kept, so a redirect written there
    (`cat <<EOF > .claude/tickets/x.json`) is still seen.

    Exception: when the heredoc feeds a shell or interpreter, the body genuinely
    IS code and is scanned. `bash <<EOF ... EOF` executes what it is handed.
    """
    lines = command.split("\n")
    kept, i = [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        match = HEREDOC_START.search(line)
        if not match:
            i += 1
            continue

        marker = match.group(2)
        end = i + 1
        while end < len(lines) and lines[end].strip() != marker:
            end += 1
        after = "\n".join(lines[end + 1:])
        body_is_code = (scan_interpreter_bodies
                        and _body_can_run(line, after, marker))
        i += 1
        while i < len(lines) and lines[i].strip() != marker:
            if body_is_code:
                kept.append(lines[i])
            i += 1
        if i < len(lines):
            kept.append(lines[i])  # the terminator
        i += 1
    return "\n".join(kept)


INTERPRETERS = {"python", "python3", "perl", "ruby", "node", "sh", "bash", "zsh"}
COMMENT = re.compile(r'(?:^|\s)#.*$')

# The SAFE side of "what happens to a heredoc body": commands that consume it
# as TEXT and cannot execute it. Everything else -- ssh, pwsh, lua, env, a
# program nobody has heard of -- is assumed to run what it is handed.
#
# A name missing from THIS set costs a visible refusal. A name missing from
# the FEEDS_CODE list it replaces was a silent pass, and three spellings
# walked through that list straight into the permanent iOS ban.
CONSUMES_TEXT = frozenset({
    "cat", "tee", "dd", "cd", "pushd", "popd",
    "grep", "egrep", "fgrep", "rg", "sort", "uniq", "wc",
    "head", "tail", "tac", "rev", "tr", "cut", "nl", "fold", "column",
    "jq", "diff", "comm", "patch", "ticket",
    "echo", "printf", "true", "false", "test", ":",
})


REDIRECT_TARGET = re.compile(r'>\|?\s*([^\s;|&<>]+)')


def _names_the_written_file(feeder_line, after):
    """True when text after the terminator refers to what the heredoc wrote.

    The destination is on the feeder line -- a redirect target, or an operand
    of a writer like `tee`. If a later statement names it, that statement can
    run it; if it names nothing the feeder wrote, it cannot.
    """
    targets = set(REDIRECT_TARGET.findall(feeder_line))
    try:
        tokens = shlex.split(feeder_line)
    except ValueError:
        return bool(after.strip())   # unreadable feeder: assume the worst
    for index, token in enumerate(tokens):
        if os.path.basename(token) in ("tee",):
            targets.update(t for t in tokens[index + 1:]
                           if not t.startswith("-"))
    for target in targets:
        if not target:
            continue
        if target in after or os.path.basename(target) in after:
            return True
    return False


def _owning_statement(feeder_line, marker=None):
    """The one statement on this line the heredoc is actually fed to.

    CE-2.29. A feeder LINE can hold several statements, and only one of them
    receives the body:

        git add guard.py && git commit -q -F - <<'MSG'

    Asking the whole line meant any statement on it could decide, and
    `git add` -- which neither consumes text nor speaks in it -- said the
    body was code. So a commit MESSAGE describing `git clean -f` was scanned
    as a command and refused, which is the CE-2.20 defect: a guard reading a
    sentence about a command as the command.

    It refused the commit that recorded the fix for it, twice in one night.

    The operator is the fact that answers this, not a list: the statement
    carrying `<<MARKER` is the statement being fed.
    """
    owners = [chunk for chunk in statements(feeder_line)
              if (HEREDOC_START.search(chunk) if marker is None else
                  any(m.group(2) == marker
                      for m in HEREDOC_START.finditer(chunk)))]
    return owners[-1] if owners else feeder_line


def _feeder_interpreter(feeder_line, marker):
    """The interpreter word this heredoc's body is CODE FOR, or None.

    CH-224.69. `_body_can_run`'s ONE case already knows the owning statement
    is an interpreter invocation -- that is what FEEDS_CODE answers. What it
    does not do is hand that word anywhere: the body lines it keeps go back
    into the command exactly as written, so `python3 <<EOF` and the line
    below it that opens a ticket file become two separate STATEMENTS once the
    splitter cuts on the newline between them, and a mutator pattern asking
    "does python3 appear on the line that writes the store" finds python3 on
    the wrong one.

    Only the ONE case answers this. TWO's case (`cat > r.sh <<EOF ...; bash
    r.sh`) has no interpreter on the owning statement -- `cat` is not one --
    so this returns None and the body is handed back untagged.
    """
    owner = _owning_statement(feeder_line, marker)
    if not FEEDS_CODE.match(owner):
        return None
    word = _WORD.search(owner)
    return os.path.basename(word.group()) if word else None


def tag_interpreter_feeders(command):
    """Prefix each already-kept heredoc body LINE with the interpreter word
    feeding it -- `python3 open('.claude/tickets/CH-1.json', 'w')...` instead
    of the bare line.

    CH-224.69. Meant to run on `strip_heredoc_bodies`' OUTPUT: every body line
    still present there is already known to be code, and this only asks WHOSE.
    A guard that judges one STATEMENT at a time ("does python3 appear where
    the store does") never sees the answer otherwise -- the interpreter's name
    lives on the feeder line, a separate statement once the newline between it
    and the body is split, and the body's own words rarely say what is running
    them. `python3 -c "...store..."` was already refused; the same write as a
    heredoc was not, because nothing carried "python3" onto the line that
    named the store.

    A heredoc whose body was dropped (data, not code) leaves nothing between
    its feeder line and its terminator here, so there is nothing to tag --
    this cannot turn a data heredoc into a tagged one.
    """
    lines = command.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        match = HEREDOC_START.search(line)
        if not match:
            i += 1
            continue

        marker = match.group(2)
        feeder = _feeder_interpreter(line, marker)
        i += 1
        while i < len(lines) and lines[i].strip() != marker:
            out.append(f"{feeder} {lines[i]}" if feeder else lines[i])
            i += 1
        if i < len(lines):
            out.append(lines[i])  # the terminator
        i += 1
    return "\n".join(out)


def _body_can_run(feeder_line, after, marker=None):
    """True when this heredoc's body is CODE rather than data.

    Two ways, and the CSO gate on 2026-09-12 reproduced both getting through.

    ONE: the feeder itself is an interpreter. FEEDS_CODE used to be matched
    against the whole line, anchored at its start, so

        cd <ios-repo> && bash <<'EOF' ... gh workflow run ... EOF

    read as "a document fed to a `cd`" and the body was dropped. Real bash
    cds and then executes it. ci_cost_guard has carried a per-STATEMENT fix
    for this since CH-237.10 defect 3, in a private copy of this function;
    Grace's finding 9 measured the divergence on 2026-09-11 and the
    mitigation was never brought here. It is here now, and that copy goes
    away.

    TWO: nobody is fed anything, and the body still runs.

        cat > /tmp/r.sh <<'EOF' ... gh workflow run ... EOF
        bash /tmp/r.sh

    The feeder genuinely is `cat`. No test of the feeder LINE can see this,
    per-statement or otherwise, because the thing that runs the body is
    somewhere else in the command. That spelling defeated the permanent iOS
    ban on both guards.

    BOTH were first answered with a list of the dangerous side, and both
    lists were walked through within the hour of being written.

    TWO's list named the things that run a file. Clyde walked `pwsh`,
    `fish`, `awk -f` and `lua` through it. ONE's list was FEEDS_CODE --
    bash, sh, zsh, python, perl, ruby, node -- and the CSO gate walked
    `ssh mac-buildbox <<EOF`, `pwsh <<EOF` and `env python3 <<EOF` through
    that, the last beating a LISTED name with one prefix word. Each
    defeated the permanent iOS ban, and the pwsh spelling also carried
    `git reset --hard` past main_branch_guard.

    So both halves ask the finite question now.

    TWO: DOES ANYTHING AFTER THE TERMINATOR REFERENCE THE FILE THE BODY WAS
    WRITTEN TO? The first answer here was "is there anything after the
    terminator at all", which is true of the dangerous case and of almost
    every harmless one. The harness's own suite caught it:

        cat > notes.md <<'DESC'
        ...prose describing a commit...
        DESC
        echo done

    `echo done` cannot run notes.md, and reading that body made prose about
    a commit into a commit -- the exact defect CE-2.20 and CE-2.26 exist to
    remove, reintroduced by my own fix for a different one.

    The file is NAMED on the feeder line, so the question is finite without
    any list: `cat > r.sh <<EOF ... EOF; bash r.sh` mentions r.sh after the
    terminator and is code; `cat > notes.md <<DESC ... DESC; echo done` does
    not mention notes.md and is data. A feeder that names no file can be
    referenced by nothing.

    ONE: DOES EVERY COMMAND ON THE FEEDER LINE MERELY CONSUME TEXT? That is
    CONSUMES_TEXT, and it is the SAFE side. A name missing from it costs a
    refusal -- visible, arguable, one line to fix. A name missing from
    FEEDS_CODE was a silent pass that spent Patrick's Actions quota.

    Stated cost, unchanged in kind and smaller in extent: a heredoc written
    to a file that a LATER statement names is read as code, so `cat > d.md
    <<EOF ... EOF && git add d.md` has its body scanned.
    """
    owner = _owning_statement(feeder_line, marker)
    if _names_the_written_file(owner, after or ""):
        return True
    for chunk in statements(owner):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            return True     # unreadable feeder is not a feeder we may trust
        head = next((t for t in tokens if not ASSIGNMENT.match(t)), None)
        if head is None:
            continue
        if os.path.basename(head) in CONSUMES_TEXT:
            continue
        # `git commit -F -` and `gh pr create --body -` take the body as a
        # MESSAGE. They are already named as text-speakers for the masker,
        # so the same table answers here rather than a second special case.
        # Measured: without this, writing a commit message that DESCRIBES a
        # destructive command was refused -- allowed at 9541b35, refused by
        # my own change, which is the over-refusal CE-2.26's AC1 exists for.
        words = _head_words(chunk)
        if any(words[:len(shape)] == list(shape)
               for shape in SPEAKS_IN_TEXT_FLAGS):
            continue
        return True
    return False


def scannable_text(command):
    """The parts of a command that are instructions, not data.

    For guards that look for a dangerous phrase. Matching the raw string cannot
    tell `git reset --hard` from `echo "git reset --hard"`, and on 2026-08-08 it
    blocked a retrospective analysis script that merely quoted the phrase, and a
    bash comment that mentioned it. That is the same defect as permitting
    `eval "..."`: a guard that cannot separate a command from a sentence about
    one fails in both directions.

    Quoted spans are blanked because an argument is data. Trailing comments are
    dropped for the same reason.

    The exception is an interpreter's -c/-e argument, which is quoted *and* is
    code: `python3 -c "...shutil.rmtree(...)"` is an instruction wearing a
    string's clothes. Those statements are scanned whole, deliberately, which
    means a harmless `python3 -c "print('git reset --hard')"` is still refused.
    That is a conservative trade, not an oversight -- the cost is a workaround,
    and the alternative is a hole.

    Ported from ticket_bash_guard.unquoted() in claude-harness, which had it
    right first. The fourth time one guard's fix had not reached its sibling.
    """
    kept = []
    # A heredoc body is data as much as a quoted argument is: a document
    # describing a command is not one. The exception is a heredoc feeding an
    # interpreter, which genuinely is code and is kept.
    for statement in statements(strip_heredoc_bodies(command)):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            # Unbalanced quotes: cannot reason about it, so hand the guard the
            # whole thing rather than a comfortable subset.
            kept.append(statement)
            continue
        if tokens and tokens[0].rsplit("/", 1)[-1] in INTERPRETERS and (
                any(is_command_flag(t) for t in tokens[1:]) or "-e" in tokens):
            kept.append(statement)
            continue
        masked = QUOTED.sub(lambda m: " " * len(m.group()), statement)
        kept.append(COMMENT.sub("", masked))
    return "\n".join(kept)


# ── variable expansion ──────────────────────────────────────────────────────
#
# 2026-09-10. A guard that matches a path by its spelling is defeated by spelling
# it differently, and the cheapest different spelling is a variable. Measured
# 2026-09-10 -- the first is refused, the second is not, and they do the same
# thing:
#
#     rm -f /home/patrick/.local/share/harness/claude-harness/tickets/CH-1.json
#     STORE=/home/patrick/.local/share/harness/claude-harness/tickets
#     rm -f "$STORE/CH-1.json"
#
# The statement splitter cuts on `;` and newlines, so the `rm` half carries no
# store path for a mutator pattern to match. I found this by accident while
# cleaning up after a probe, which is the only reason it was found at all.
#
# Two sources, and between them they cover what a shell would actually expand:
#
#   1. Assignments in the SAME command string. This is the whole realistic
#      surface, because Claude Code's Bash tool does not persist shell state
#      between calls -- a variable used in a mutating command has to be
#      assigned in that same command, or it is empty.
#   2. The hook's own environment, for names it did not see assigned. `$HOME`
#      is the one that matters: it survives from the profile, it resolves, and
#      `"$HOME/.local/share/harness/..."` reaches the store without the literal
#      prefix ever appearing.
#
# Single quotes are respected, because the shell respects them: `'$STORE'` is
# not expanded by bash, so a guard that expanded it would refuse a command that
# could never have reached the store. A guard that refuses harmless operations
# teaches everyone to route around it.
ASSIGNMENT = re.compile(r"""
    (?:^|[;\n&|]|\bexport\s+)\s*
    ([A-Za-z_][A-Za-z0-9_]*)=
    (?: "([^"]*)" | '([^']*)' | ([^\s;|&]*) )
""", re.VERBOSE)

VARIABLE = re.compile(r'\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))')

EXPANSION_ROUNDS = 3


def assignments_in(command):
    """Every NAME=value assigned in this command string."""
    found = {}
    for m in ASSIGNMENT.finditer(command):
        value = next((g for g in m.groups()[1:] if g is not None), "")
        found[m.group(1)] = value
    return found


def _substitute(text, values):
    """Replace known $NAME and ${NAME} everywhere bash would.

    Quote state is tracked as bash tracks it, and the nesting is the part that
    matters: inside double quotes a single quote is an ORDINARY CHARACTER, not
    a delimiter. So in

        python3 -c "open('$S/CH-1.json','w')"

    bash expands `$S` -- the inner quotes are literal text within the double
    quotes. An expander that treated them as a single-quoted span would leave
    `$S` alone and hand a guard a statement with no path in it. That exact
    shape was the last surviving leak in the 2026-09-10 evasion matrix.
    """
    out = []
    i = 0
    in_single = False
    in_double = False
    while i < len(text):
        ch = text[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if ch == "$" and not in_single:
            m = VARIABLE.match(text, i)
            if m:
                name = m.group(1) or m.group(2)
                if name in values:
                    out.append(values[name])
                    i = m.end()
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


def expand_assignments(command, env=None):
    """`command` with variables it can resolve substituted in.

    Best-effort and deliberately so: command substitution, arrays and indirect
    expansion are not resolved, and a name from neither source is left alone
    (an unset variable expands to nothing in a real shell, which does not reach
    a store either). It closes the spelling an agent actually reaches for.

    Bounded rounds so `A=/x; B=$A/y; rm "$B/z"` resolves without a
    self-referential pair spinning.
    """
    values = dict(os.environ if env is None else env)
    values.update(assignments_in(command))

    expanded = command
    for _ in range(EXPANSION_ROUNDS):
        nxt = _substitute(expanded, values)
        if nxt == expanded:
            break
        expanded = nxt
    return expanded


SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "ash"}
# Interpreters whose payload is SOURCE, not shell. Token-parsing python is
# fiction, so a caller gets the text and applies its own raw-text fallback.
# Deliberately distinct from INTERPRETERS above, which answers a different
# question (does this take code as an argument at all) and therefore includes
# the shells.
CODE_INTERPRETERS = {"python", "python3", "perl", "ruby", "node"}

# Commands whose job is to run ANOTHER command. Each needs its own option
# grammar, because a flag whose value is eaten as a command -- or a bare
# operand read as one -- is the same class of bug as reading `-c`'s value as
# the payload (CH-237.4).
#
# CE-2.20 replaced four guards' raw-text matching with a token parser that
# read argv0 ONLY, and the CSO gate caught what that cost on 2026-09-11:
#
#     timeout 900 gh workflow run ios.yml     main: deny   ->  SILENT
#     ssh build-box gh workflow run ios.yml   main: deny   ->  SILENT
#
# A metered macOS dispatch with no gate anywhere, where the string match it
# replaced had refused it. Trading a false positive for a false negative is
# not a fix, and `timeout` is this box's own incident wrapper -- the
# 2026-09-10 orphan leak was `timeout 900 claude -p`.
#
#   value_flags  options that consume the token after them
#   operands     bare words belonging to the wrapper rather than to the
#                command (timeout's DURATION, ssh's destination)
WRAPPERS = {
    "sudo": {"value_flags": ("-u", "-g", "-p", "-C", "-U", "-r", "-t"), "operands": 0},
    "env": {"value_flags": ("-u", "--unset", "-C", "--chdir", "-S"), "operands": 0},
    "nohup": {"value_flags": (), "operands": 0},
    "nice": {"value_flags": ("-n", "--adjustment"), "operands": 0},
    "command": {"value_flags": (), "operands": 0},
    "exec": {"value_flags": ("-a",), "operands": 0},
    "xargs": {"value_flags": ("-n", "-L", "-I", "-P", "-s", "-a", "-d", "-E"),
              "operands": 0},
    "setsid": {"value_flags": (), "operands": 0},
    "stdbuf": {"value_flags": ("-i", "-o", "-e", "--input", "--output", "--error"),
               "operands": 0},
    "timeout": {"value_flags": ("-s", "--signal", "-k", "--kill-after"), "operands": 1},
    "ssh": {"value_flags": ("-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J",
                            "-L", "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S",
                            "-W", "-w"), "operands": 1},
}
# Wrappers that run the command on ANOTHER machine. A caller resolving
# anything against the local disk would be answering about the wrong box.
REMOTE_WRAPPERS = {"ssh"}


def strip_wrappers(tokens):
    """(argv, remote) with every wrapper peeled off.

    argv is None when the wrappers consumed everything -- `ssh host` with no
    command is a login, not an invocation. remote is True once any wrapper in
    REMOTE_WRAPPERS has been crossed, and stays true for what lies behind it.
    """
    remote = False
    while tokens:
        argv0 = os.path.basename(tokens[0])
        spec = WRAPPERS.get(argv0)
        if spec is None:
            return tokens, remote
        if argv0 in REMOTE_WRAPPERS:
            remote = True
        rest = tokens[1:]
        if argv0 == "env":
            # env's leading arguments are assignments until the first bare word.
            while rest and ASSIGNMENT.match(rest[0]):
                rest = rest[1:]
        while rest and rest[0].startswith("-") and rest[0] != "--":
            rest = rest[2:] if rest[0] in spec["value_flags"] else rest[1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        for _ in range(spec["operands"]):
            if not rest:
                return None, remote
            rest = rest[1:]
        tokens = rest
    return None, remote


def payload_of(argv0, rest):
    """The code a shell or interpreter was handed to run, or None.

    None means there is nothing to descend into: a bare word is a script FILE,
    and a flag's value is not the payload. Both distinctions are load-bearing
    -- `bash -o posix -c '...'` hid a forged UAT verdict behind the first and
    `bash script.sh` would invent one behind the second.
    """
    if argv0 == "eval":
        return " ".join(rest)
    i = 0
    while i < len(rest):
        token = rest[i]
        if token in FLAGS_TAKING_A_VALUE:
            i += 2
            continue
        if is_command_flag(token) or (argv0 in CODE_INTERPRETERS and token == "-e"):
            return rest[i + 1] if i + 1 < len(rest) else None
        if token.startswith("-"):
            i += 1
            continue
        return None  # a bare word is a script file, not a payload
    return None


def gh_subcommand_at(argv, *names):
    """True when this argv runs `gh` with `names` as its subcommand path.

    Positional, not argv[1:len(names)+1]: gh's global flags may precede the
    subcommand, and `gh -R owner/repo workflow run ios.yml` dispatches exactly
    as hard as the bare spelling does. Two guards checked the fixed slot and
    both were walked past by the flag (CE-2.20).
    """
    if not argv or os.path.basename(argv[0]) != "gh":
        return False
    rest, n = argv[1:], len(names)
    return any(tuple(rest[i:i + n]) == names for i in range(len(rest) - n + 1))


def dispatches_a_workflow(argv):
    """True when this argv starts a billable GitHub Actions run.

    Every spelling, in one place, because ci_cost_guard and deploy_guard both
    need this question answered and answering it twice is how they came to
    disagree. Rerunning a run re-bills it in full, so the rerun endpoint is in
    the class alongside dispatches -- the class is about spend, not about which
    gh verb starts it (CH-237.10).
    """
    if gh_subcommand_at(argv, "workflow", "run") or gh_subcommand_at(argv, "run", "rerun"):
        return True
    if not argv or os.path.basename(argv[0]) != "gh":
        return False
    rest = argv[1:]
    return "api" in rest and any(
        "dispatches" in a or a.rstrip("/").endswith("/rerun") for a in rest)


def _mask_inert(text):
    """Blank the spans where shell syntax is inert, keep the spans where it is not.

    Single quotes make everything inside literal, so the whole span is data.
    Double quotes do NOT disable command substitution, so `$`, `(`, `)` and a
    backtick stay visible inside them and the rest is blanked. Blanking rather
    than deleting keeps offsets, so a construct is never created by two
    fragments closing up against each other.
    """
    out, quote, i = [], None, 0
    while i < len(text):
        char = text[i]
        if quote is None:
            out.append(" " if char in "\"'" else char)
            if char in "\"'":
                quote = char
        elif char == quote:
            out.append(" ")
            quote = None
        elif quote == '"' and text.startswith("$(", i):
            # Only `$(` and a backtick survive double quotes. A BARE paren does
            # not: inside double quotes `(` is an ordinary character, so
            # keeping it would refuse `--title "why (gh workflow run) is
            # gated"` -- the exact false positive this ticket was opened to
            # remove, reintroduced by the fix for its opposite.
            out.append("$(")
            i += 2
            continue
        elif quote == '"' and char == "`":
            out.append(char)
        else:
            out.append(" ")
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# The safe side.
#
# Grace, 2026-09-11, finding 1: "Ask the opposite question, and enumerate the
# safe side, which is small and knowable."
#
# What stood below this was the dangerous side: eleven wrappers to peel, eight
# indirection regexes, twelve keyword names, and everything absent from those
# lists treated as a leaf command doing its own work. Nine ordinary wrappers
# walked past it -- taskset, flock, docker run, poetry run, strace, chroot,
# runuser, script -qc, busybox sh -c -- and the list could never close:
# nsenter, unshare, ionice, chrt, torify, proxychains, valgrind, direnv exec,
# uv run, npm run, just, make, and any shell script on disk all run a command
# that walk would not look at.
#
# The asymmetry is the whole argument. A name missing from WRAPPERS was a
# SILENT PASS. A name missing from the allowlist here is a REFUSAL: visible,
# arguable, and one line to fix when it is wrong. That is the direction this
# repo's standing rule already picks -- everything unknown blocks.
#
# So a quoted span counts as data ONLY when the head of its statement is a
# command that consumes arguments as text. Everything else leaves the span
# visible, and a matcher run over the result sees the act sitting in it.

# `gh`'s own global flags may sit between the binary and its subcommand, so
# strict adjacency misses `gh -R owner/repo workflow run` -- a real dispatch,
# pinned by fixture 10 since CH-237.10. Allowing FLAGS between them is not the
# old `.*` looseness: `gh run list --workflow ci.yml` still does not match,
# because `run list` is not `workflow run`. One definition, shared, because
# writing this twice is how the two guards drifted apart before.
GH_FLAGS = r'(?:-[A-Za-z-]+(?:=\S+)?(?:\s+[^\s-]\S*)?\s+)*'

# Heads where EVERY quoted span in the statement is text.
SPEAKS_ENTIRELY_IN_TEXT = frozenset({"ticket", "jq", "printf", "echo"})

# Heads where only the values of named flags are text. Keeping this narrow is
# what stops `git -c alias.z='!...' commit` from being masked by the presence
# of `commit` elsewhere on the line.
SPEAKS_IN_TEXT_FLAGS = {
    ("git", "commit"): ("-m", "--message"),
    ("gh", "pr", "create"): ("--title", "-t", "--body", "-b"),
    ("gh", "issue", "create"): ("--title", "-t", "--body", "-b"),
}

_QUOTED_SPAN = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_WORD = re.compile(r'\S+')


def _statement_spans(command):
    """(start, end) of each statement, as offsets into the original text.

    `statements()` yields text and drops separators, which is right for its
    callers and wrong here: this has to rebuild a string the same LENGTH as
    the input, so a match position still points at the right place.
    """
    masked = _mask_inert(command)
    spans, start = [], 0
    for match in STATEMENT_SPLIT.finditer(masked):
        # A text-speaking head is safe only when its output goes to a
        # PERSON. Piped into a command, or redirected into a file that
        # something later runs, the text is the act rather than a message
        # about it -- `printf '<act>' | bash` and `echo '<act>' > f.sh &&
        # bash f.sh` are both the act. So a statement that is piped, or that
        # redirects, keeps its spans visible however safe its head looks.
        fragment = command[start:match.start()]
        consumed = match.group() == "|" or ">" in _mask_inert(fragment)
        spans.append((start, match.start(), consumed))
        start = match.end()
    tail = command[start:]
    spans.append((start, len(command), ">" in _mask_inert(tail)))
    return [(a, b, piped) for a, b, piped in spans if b > a]


# git's global options sit between `git` and its subcommand. These take their
# value as the next word; attached spellings (`-C<dir>`, `--git-dir=<path>`) and
# flags such as --no-pager are a single word.
GIT_OPTIONS_TAKING_A_VALUE = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
})


def _head_words(fragment):
    """The leading words of a statement, past any VAR=value assignments.

    For git, past its global options as well. 2026-09-14: `git -C <dir> commit
    -F -` read as ["git", "-C", "<dir>"], matched no shape in
    SPEAKS_IN_TEXT_FLAGS, and its commit message was scanned as commands --
    so ticket_bash_guard refused the commit that shipped its --allow-dirty
    check, on a message line naming a ticket and the flag.
    """
    words = _WORD.findall(fragment)
    index = 0
    while index < len(words) and ASSIGNMENT.match(words[index]):
        index += 1
    if index < len(words) and os.path.basename(words[index]) == "git":
        rest = words[index + 1:]
        i = 0
        while i < len(rest) and rest[i].startswith("-"):
            i += 2 if rest[i] in GIT_OPTIONS_TAKING_A_VALUE else 1
        return ["git"] + [os.path.basename(w) for w in rest[i:i + 2]]
    return [os.path.basename(w) for w in words[index:index + 3]]


def _span_runs_something(span):
    """True when this quoted span EXECUTES before its head ever reads it.

    Single quotes are literal and this returns False for them. Double quotes
    are not: `$( )` and backticks substitute INSIDE them, so the command runs
    first and the safe head receives its output. A head that speaks in text
    never touches the act at all, which is why masking the span on the head's
    behalf hides it completely.

    CE-13.6 QA round 1, and it is a regression this story caused: six of these
    seven were refused by BOTH guards at the parent, because the deleted
    INDIRECTION list happened to name command substitution. Deleting the
    wrapper walk took that with it.

        echo "$(gh workflow run ci.yml)"
        echo "`gh workflow run ci.yml`"
        git commit -m "done: $(gh workflow run ci.yml) verified"
        gh pr create --title release --body "$(gh workflow run ci.yml)"
        printf '%s' "$(gh workflow run ci.yml)"

    The module already said so one function away -- `_mask_inert`: "Double
    quotes do NOT disable command substitution." The masker was written as
    though they did.
    """
    if not span.startswith('"'):
        return False
    return "$(" in span or "`" in span


def _data_spans_of(fragment, offset):
    """Absolute (start, end) of every quoted span that is DATA here."""
    head = _head_words(fragment)
    if not head:
        return []

    if head[0] in SPEAKS_ENTIRELY_IN_TEXT:
        # A head that speaks entirely in text speaks in UNQUOTED text too.
        # `echo we do not gh workflow run here` has no quotes for the span
        # masker to find, so the words stayed visible and the matcher read
        # an echo of prose as the act. Measured as a new refusal in 2 of 130
        # guard-payload pairs when heredoc bodies started being read
        # (CE-13.8): an ssh body saying the phrase rather than doing it.
        #
        # Everything after the head is its argument, so mask it -- UNLESS
        # something in the fragment can RUN, because it runs before the head
        # ever sees it.
        #
        # The first version listed the two spellings I had in mind, `$(` and
        # a backtick. The CSO gate walked `echo <(gh workflow run x)` through
        # it within the hour: process substitution holds neither, bash
        # executes it, and both guards went silent where both had refused at
        # the parent commit. That reopened the permanent iOS ban.
        #
        # So this asks the question the other way. A parenthesis, a dollar or
        # a backtick anywhere in the fragment means something here may run,
        # and the fragment falls back to the quoted-span behaviour that
        # already refuses it. Plain words are plain words; anything with
        # shell machinery in it is not, and no spelling needs naming.
        if not any(c in fragment for c in "$`()"):
            after_head = fragment.find(head[0]) + len(head[0])
            return [(offset + after_head, offset + len(fragment))]
        return [(offset + m.start(), offset + m.end())
                for m in _QUOTED_SPAN.finditer(fragment)
                if not _span_runs_something(m.group())]

    flags = None
    for shape, named in SPEAKS_IN_TEXT_FLAGS.items():
        if head[:len(shape)] == list(shape):
            flags = named
            break
    if flags is None:
        return []

    out = []
    for match in _QUOTED_SPAN.finditer(fragment):
        if _span_runs_something(match.group()):
            continue
        before = fragment[:match.start()].rstrip()
        words = before.split()
        last = words[-1] if words else ""
        if last in flags or any(last.endswith(f + "=") for f in flags):
            out.append((offset + match.start(), offset + match.end()))
    return out


def mask_data_spans(command):
    """Blank the quoted spans that are genuinely data; keep everything else.

    The result is the same length as the input, so a match position still
    means something. An assignment's right-hand side is never masked, because
    something later expands it.
    """
    text = command or ""
    keep = list(text)
    for start, end, piped in _statement_spans(text):
        if piped:
            continue
        for a, b in _data_spans_of(text[start:end], start):
            for i in range(a, b):
                keep[i] = " "
    return "".join(keep)


# Shell constructs that can carry a command the token walk does not see.
#
# CE-2.20, third attempt, found by the GLM QA pass on 2026-09-11. The second
# attempt treated "it tokenised" as "I understood it", and the fail-closed
# raw-text fallback fired only when NOTHING parsed. So a command that parsed
# perfectly while hiding its payload sailed through, and THIRTEEN spellings
# that a raw string match had denied went silent:
#
#     (gh workflow run x)          if gh workflow run x; then ...
#     echo $(gh workflow run x)    `gh workflow run x`
#     while ...; do ...            { gh workflow run x; }
#     time / ! / <() / env -S      echo '...' | bash
#
# Parsing is not the same as seeing. When one of these is present the walk is
# NOT authoritative, and the caller falls back to its own text match -- which
# is exactly as conservative as the guard was before CE-2.20 touched it. The
# false-positive fix is unaffected: an ordinary `ticket new --title "...gh
# workflow run..."` has its words inside quotes and parses clean.
# INDIRECTION, and the shape of this changed on 2026-09-11. What stood here
# was a finite enumeration of constructs known to hide a command, and it was
# defeated three times running -- each time by a construct nobody had listed:
# wrappers, then shell syntax, then indirection (here-strings, variable
# expansion, `find -exec`, `env --split-string`, watch, tmux, coproc, aliases,
# ANSI-C quoting).
#
# A blacklist cannot win this, and the asymmetry says why: a construct MISSING
# from the list reads as "fully seen" and yields a silent pass, which is the
# expensive direction. So the question is inverted. Authority is granted only
# to text that is plainly nothing but commands and separators; anything else,
# recognised or not, costs a raw-text match -- exactly as conservative as
# these guards were before CE-2.20 touched them.
INDIRECTION = (
    re.compile(r'\$'),                   # any expansion: $(..), $VAR, $'..'
    re.compile(r'`'),                    # the older command substitution
    re.compile(r'<<<'),                  # here-string
    re.compile(r'<\(|>\('),              # process substitution
    re.compile(r'(?:^|\s)\(|\)(?:\s|$)'),        # a subshell
    re.compile(r'(?:^|\s)[{}](?:\s|$)'),         # a brace group
    re.compile(r'\|\s*(?:\S*/)?(?:bash|sh|zsh|dash|ksh|python3?|perl|ruby|node)\b'),
    re.compile(r'(?:^|\s)env\s+(?:-S|--split-string)'),
)
# Keywords whose operand is a command. `time`/`!`/`coproc` take one directly;
# the rest introduce a list. In every case the verb sits somewhere the argv0
# scan does not look.
COMMAND_KEYWORDS = frozenset({
    "if", "then", "elif", "else", "fi", "while", "until", "for", "do", "done",
    "case", "esac", "select", "time", "!", "coproc",
})
# argv0s that run a command this text does not show: read from stdin, from a
# substitution placeholder, from the alias table, or from a file. Peeling them
# reveals nothing, so the walk cannot be authoritative over them.
RUNS_UNSEEN = frozenset({
    "eval", "xargs", "find", "watch", "tmux", "screen", "parallel",
    "alias", "source", ".", "at", "batch",
})


def parse_sees_everything(command):
    """True only when this text is plainly commands and separators.

    Errs toward False, and now actually does. The old implementation said so
    in this same docstring while enumerating hiding places, so every construct
    absent from that list fell through to True -- the docstring and the code
    were opposite, and three QA rounds each found a different construct in the
    gap between them.

    A wrong False costs a raw-text match. A wrong True is a silent hole.
    """
    masked = _mask_inert(CONTINUATION.sub("", command or ""))
    if any(pattern.search(masked) for pattern in INDIRECTION):
        return False
    for chunk in statements(masked):
        words = chunk.split()
        index = 0
        while index < len(words) and ASSIGNMENT.match(words[index]):
            index += 1
        if index >= len(words):
            continue
        head = words[index]
        # Position matters, and checking every word instead refused `ticket
        # move X --to done` -- this repo's daily syntax -- because `done` ends
        # a loop somewhere else. A keyword is a keyword where a command may
        # start; anywhere else it is just a word in an argument.
        if head in COMMAND_KEYWORDS:
            return False
        if os.path.basename(head) in RUNS_UNSEEN:
            return False
    return True


def resolved_commands(command):
    """Every real command in this shell text: ((argv, source, remote), ...), parsed.

    Wrappers are peeled and shell payloads are descended, so the thing a guard
    matches on is what the shell will actually run rather than what the string
    happens to start with.

      argv    the command's tokens, or None when what was found is SOURCE
              rather than shell (a python/ruby/node payload) and tokenising it
              would be fiction -- the caller applies its own raw-text match to
              `source` in that case.
      source  the payload the command was found inside, so a caller resolving a
              working directory honours the payload's own `cd`; None at the
              top level.
      remote  True when it runs on another machine.

    `parsed` is False ONLY when nothing in the command could be read at all.
    That is not the same as finding nothing, and a caller must fail closed on
    it -- ci_cost_guard's predecessor conflated the two and let a dispatch
    through because the statement list was full of tokens that merely failed to
    look like what they were (CH-237.9).
    """
    found, parsed = [], False

    def walk(tokens, source, remote):
        argv, crossed = strip_wrappers(tokens)
        remote = remote or crossed
        if not argv:
            return
        if crossed and os.path.basename(tokens[0]) in REMOTE_WRAPPERS:
            # What follows a remote wrapper is a command STRING that the REMOTE
            # shell parses, not an argv. `ssh host gh workflow run x` and
            # `ssh host 'gh workflow run x'` are one instruction spelled twice,
            # and shlex keeps the second as a SINGLE token whose argv0 is the
            # whole command -- so the quoted spelling walked straight past the
            # wrapper walk while the bare one was caught. Found by the QA pass
            # on 2026-09-11 by adding one quote pair to this repo's own
            # fixture 08. Rejoining and re-reading it as shell answers both.
            for chunk in statements(" ".join(argv)):
                try:
                    sub = shlex.split(chunk)
                except ValueError:
                    continue
                while sub and ASSIGNMENT.match(sub[0]):
                    sub = sub[1:]
                if sub:
                    walk(sub, source, True)
            return
        argv0 = os.path.basename(argv[0])
        if argv0 in SHELLS or argv0 in CODE_INTERPRETERS or argv0 == "eval":
            code = payload_of(argv0, argv[1:])
            if code and argv0 in CODE_INTERPRETERS:
                found.append((None, code, remote))
                return
            if code:
                for chunk in statements(code):
                    try:
                        sub = shlex.split(chunk)
                    except ValueError:
                        continue
                    while sub and ASSIGNMENT.match(sub[0]):
                        sub = sub[1:]
                    walk(sub, source or code, remote)
                return
        found.append((argv, source, remote))

    for statement in statements(command or ""):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        parsed = True
        while tokens and ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
        walk(tokens, None, False)
    # Tokenising is not understanding. If the text carries a construct this
    # walk cannot see into, the walk is not authoritative however much of it
    # parsed, and the caller must fall back rather than trust it.
    return tuple(found), parsed and parse_sees_everything(command)


# The git flags that name where a command runs. --work-tree is here because
# GIT_GLOBAL_FLAGS_WITH_VALUE below already counts it a value-taking flag: a
# tuple that omits it here is the sibling-list drift this file's comments warn
# about (CH-237.10).
PATH_FLAGS = ("-C", "--git-dir", "--work-tree")


def path_flag_values(tokens):
    """Values of every repo-locating git flag, in token order.

    Both spellings of each: `-C path` and `-Cpath`, `--git-dir path` and
    `--git-dir=path`. Exact-token membership answers only the separated forms,
    while `git -Cios push` is a command git runs happily -- and the guard
    resolves the session repo, judging a push it has no business approving.

    A separated flag's value is skipped so it is not itself read as a flag.
    """
    values = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in PATH_FLAGS:
            if i + 1 < len(tokens):
                values.append(tokens[i + 1])
            i += 2
            continue
        if token.startswith("--") and "=" in token:
            name, _, attached = token.partition("=")
            if name in PATH_FLAGS:
                values.append(attached)
        elif token.startswith("-C") and len(token) > 2:
            values.append(token[2:])
        i += 1
    return values


def target_directory(command, default=None):
    """The directory the git commands in `command` will run in.

    Honours a leading `cd <path>`, which applies to everything after it, and
    `git -C <path>` / `--git-dir <path>` / `--work-tree <path>`, which apply to
    one invocation and win as the more specific. Unresolvable paths (a shell
    variable this cannot expand) fall back to the shell's directory, which
    keeps the behaviour conservative rather than guessing.

    A `-C` does not move the shell, so it must not outlive its own statement
    (CH-237.10): `cd ios && git -C other status && git push` -- the push runs
    from ios, and the LAST git invocation decides, from its own flags if it
    carries any that resolve, else from the shell's directory there.

    A `cd` inside a subshell moves the shell only while the parens hold, so a
    cd is tracked at the depth it runs at and dropped when the parens close:
    `(cd ios && git push)` runs its push from ios; `(cd ios) && git push` does
    not. `pushd` moves the shell exactly as `cd` does.

    `default` is the payload's `cwd`, and passing it is not optional. Hooks run
    with the process working directory set to the session directory, which is
    whatever repo the session was started in -- not the repo the command
    targets. Falling back to os.getcwd() makes a guard silently dormant on every
    repo except the session's own, which reads exactly like a guard that
    approves.
    """
    cwd = default or os.getcwd()
    judged = None   # directory of the last git invocation seen
    depth = 0
    cwds = [cwd]    # cwds[d]: the shell's directory at subshell depth d

    def resolve(path, base):
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        path = os.path.normpath(path)
        return path if os.path.isdir(path) else None

    for statement in statements(command or ""):
        # Parens are counted on a quote-masked copy: a '(' inside an argument
        # is text, not syntax. Leading '(' open the subshell these commands
        # run in; the net count sets the depth of everything after them.
        masked = QUOTED.sub(lambda m: " " * len(m.group()), statement)
        lead = len(statement) - len(statement.lstrip("("))
        level = depth + lead
        while len(cwds) <= level:
            cwds.append(cwds[-1])
        body = statement.lstrip("(").strip()
        try:
            # shlex, not split(): a quoted path with spaces splits into separate
            # tokens under whitespace splitting, the flag lookup misses, and the
            # guard silently resolves the wrong repo.
            tokens = shlex.split(body)
        except ValueError:
            tokens = []
        if tokens:
            if tokens[0] in ("cd", "pushd") and len(tokens) > 1:
                moved = resolve(tokens[1], cwds[level])
                if moved:
                    cwds[level] = moved
            # Matched against the statement body rather than tokens[0]: a
            # leading env assignment or `sudo` would otherwise hide the
            # invocation, and a leading '(' opens a subshell rather than
            # naming a command.
            if GIT_INVOCATION.match(body):
                judged = cwds[level]
                for value in path_flag_values(tokens):
                    named = resolve(value, cwds[level])
                    if named:
                        # --git-dir names the REPOSITORY directory, not the
                        # work tree, and a guard handed <repo>/.git learns
                        # nothing: `git rev-parse --show-toplevel` fails outright
                        # inside one, so the caller falls back and judges the
                        # session instead of the repo the command named. The
                        # work tree is its parent (CH-237.10).
                        if os.path.basename(named) == ".git":
                            named = os.path.dirname(named) or named
                        judged = named
        depth = max(0, depth + masked.count("(") - masked.count(")"))
        # Below the closing parens the shell is where it was before them, so
        # deeper entries are dropped rather than left to leak into the next
        # subshell.
        del cwds[depth + 1:]
        # A non-leading '(' with no matching ')' -- `wc -l (weird` -- grows
        # depth past the end of the ladder, and cwds[depth] below indexed
        # off the end: IndexError, and a crashed guard allows everything.
        # The ladder heals instead: an untracked deeper subshell inherits
        # its parent's directory, which is what the leading-paren growth
        # above already assumes.
        while len(cwds) <= depth:
            cwds.append(cwds[-1])

    return judged or cwds[depth]


def enter_target_repo(hook_input):
    """chdir to the repo the command is about. Returns the directory.

    Call this once, early. Every subsequent bare git call is then correct
    without touching the call site -- which is why 28 hooks could be fixed
    without rewriting their internals.
    """
    tool_input = (hook_input or {}).get("tool_input") or {}
    command = tool_input.get("command", "")
    session_cwd = (hook_input or {}).get("cwd") or os.getcwd()
    target = target_directory(command, default=session_cwd)
    try:
        os.chdir(target)
    except OSError:
        return os.getcwd()
    return target


GIT_GLOBAL_FLAGS_WITH_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace")


def commit_tokens(command):
    """argv of a real `git commit` in `command`, else None.

    Token-based on purpose. A regex for `\\bcommit\\b` anywhere in the string
    also matches `git checkout -b fix/commit-gate`, a message quoting the word,
    and any path containing it. On 2026-08-08 exactly that pattern blocked the
    creation of a branch whose name contained "commit".

    Returns [] when a statement starts with git and cannot be parsed, so
    callers can fail closed on it.
    """
    import shlex
    for statement in statements(command or ""):
        if not GIT_INVOCATION.match(statement):
            continue
        try:
            tokens = shlex.split(statement)
        except ValueError:
            if re.search(r'\bcommit\b', statement):
                return []
            continue
        i = tokens.index("git") + 1 if "git" in tokens else 1
        while i < len(tokens):
            if tokens[i] in GIT_GLOBAL_FLAGS_WITH_VALUE:
                i += 2
                continue
            if tokens[i].startswith("-"):
                i += 1
                continue
            break
        if i < len(tokens) and tokens[i] == "commit":
            return tokens
    return None


def workspace_repos(session_cwd=None):
    """Every git repo a subagent in this workspace could plausibly touch.

    Agent events carry no command, so target_directory() cannot help: it falls
    back to the session cwd, which is why the working-tree guard only ever
    watched one repository. A subagent that wandered into a sibling repo left
    no trace the guard could see.

    Resolution order:
      1. CLAUDE_WORKSPACE_ROOTS -- colon-separated directories to scan
      2. <session repo>/.claude/workspace-repos.json -- {"roots": [...]}
      3. the parent of the session repo (siblings), which is the usual layout

    Returns absolute paths, session repo first, deduplicated. Worktrees under
    .claude/worktrees are excluded: they are separate git dirs whose churn is
    the isolation working, not wander.
    """
    session_cwd = session_cwd or os.getcwd()
    session_repo = repo_root(session_cwd)

    roots = []
    env = os.environ.get("CLAUDE_WORKSPACE_ROOTS", "").strip()
    if env:
        roots = [r for r in env.split(os.pathsep) if r]
    elif session_repo:
        config = os.path.join(session_repo, ".claude", "workspace-repos.json")
        if os.path.exists(config):
            try:
                import json
                with open(config) as fh:
                    roots = list(json.load(fh).get("roots") or [])
            except Exception:
                roots = []
        if not roots:
            roots = [os.path.dirname(session_repo)]

    found = []
    if session_repo:
        found.append(session_repo)
    for root in roots:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            continue
        for name in entries:
            path = os.path.join(root, name)
            if os.path.isdir(os.path.join(path, ".git")) and ".claude/worktrees" not in path:
                found.append(os.path.realpath(path))

    seen, ordered = set(), []
    for path in found:
        real = os.path.realpath(path)
        if real not in seen:
            seen.add(real)
            ordered.append(real)
    return ordered


def current_branch(cwd=None):
    """Current branch, or None if it cannot be determined.

    `branch --show-current` rather than `rev-parse --abbrev-ref HEAD`: rev-parse
    fails on an unborn branch, which made the first commit in a new repo
    impossible once undetectable branches began failing closed.

    A detached HEAD reports empty and is returned as None -- it could be
    sitting on the trunk's commit and there is no way to prove otherwise.
    """
    for argv in (["git", "branch", "--show-current"],
                 ["git", "rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=5, cwd=cwd or os.getcwd())
        except Exception:
            return None
        if r.returncode == 0:
            return r.stdout.strip() or None
    return None


def repo_root(cwd=None):
    """Top level of the work tree containing `cwd`, or None."""
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5,
                           cwd=cwd or os.getcwd())
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def target_data_file(hook_input, *relative_parts):
    """A hook's data file, resolved from the repo being JUDGED.

    CH-58. Three hooks built their data paths from their own location:

        REPO_ROOT = dirname(__file__)/../..          # this is claude-env, always
        STATUS_FILE = REPO_ROOT/infrastructure/wsl/ac-status.json

    A hook installed once and wired globally lives in claude-env, so that
    expression names claude-env no matter which repository the command or the
    write is about. ac_staleness_guard read claude-env's acceptance-criteria
    status while judging a push from photo-portfolio; artifact_path_guard looked
    for a registry that does not exist here at all and, finding none, returned
    silently on every write it was supposed to inspect.

    Same defect as the cwd bugs of 2026-08-07 -- a hook deciding about a repo
    other than the one in front of it -- in the file-reading hooks, which were
    never audited after the git-state ones were fixed.

    Resolution order, most specific first:
      1. an explicit `cd` in the command, or the payload's cwd (Bash hooks)
      2. the work tree containing the file being written (Write/Edit hooks)
      3. nothing -- the caller goes dormant

    Returns None when the file is absent, which is the dormancy contract the
    endpoint guards already use: a hook whose configuration is not present in
    this repo has nothing to say about it, and saying nothing is correct rather
    than a failure to report.
    """
    hook_input = hook_input or {}
    tool_input = hook_input.get("tool_input") or {}

    candidates = []
    command = tool_input.get("command", "")
    if command:
        candidates.append(target_directory(command, default=hook_input.get("cwd")))
    written = tool_input.get("file_path") or tool_input.get("path") or ""
    if written:
        start = os.path.dirname(os.path.abspath(written)) or None
        candidates.append(repo_root(start) if os.path.isdir(start or "") else None)
    if hook_input.get("cwd"):
        candidates.append(hook_input["cwd"])

    for base in candidates:
        if not base:
            continue
        root = repo_root(base) or base
        path = os.path.join(root, *relative_parts)
        if os.path.isfile(path):
            return path
    return None


# ── where a repo's ticket store lives ───────────────────────────────────────
#
# CH-110 moved the store OUT of the working tree, to
# `<data home>/harness/<repo>/tickets`. gate_git_commit.py did not move with
# it: it kept looking for `<repo>/.claude/tickets`, found nothing, concluded no
# ticket was in progress, and so prompted for approval on every single
# ticket-driven commit -- the exemption it was written to provide could never
# fire. Nobody noticed because a gate that asks too often looks like a gate
# that works.
#
# That is the second time this shape has bitten: ticket_store_guard's own
# docstring says "a guard carrying a private copy of where the store lives is
# one change away from guarding a directory nothing writes to". It builds the
# path from the CLI's constants for exactly this reason. claude-env's hooks
# cannot import the harness CLI -- it is a different repo and may not be
# present -- so the resolution lives HERE, once, and every hook asks it.

DATA_SUBDIR = "harness"
STORE_SUBDIR = "tickets"
LEGACY_STORE = os.path.join(".claude", "tickets")


def data_home():
    """$XDG_DATA_HOME, or the spec's default. Respected, not merely read."""
    return (os.environ.get("XDG_DATA_HOME")
            or os.path.join(os.path.expanduser("~"), ".local", "share"))


def main_checkout(root):
    """The directory `root` belongs to -- the same one for every checkout.

    A worktree's `.git` is a FILE reading `gitdir: <main>/.git/worktrees/<n>`,
    so the main checkout is two levels above that `.git` component. A SUBMODULE
    has the same shape but points at `<super>/.git/modules/<n>`; following that
    would hand it the superproject's tickets, so only the `worktrees` shape is
    followed. Mirrors ticket.py's function of the same name.
    """
    root = os.path.abspath(root)
    marker = os.path.join(root, ".git")
    if not os.path.isfile(marker):
        return root
    try:
        with open(marker) as fh:
            pointer = fh.read().strip()
    except OSError:
        return root
    if not pointer.startswith("gitdir:"):
        return root
    target = os.path.abspath(os.path.join(root, pointer.split(":", 1)[1].strip()))
    parts = target.split(os.sep)
    if len(parts) >= 3 and parts[-2] == "worktrees" and parts[-3] == ".git":
        return os.sep.join(parts[:-3]) or os.sep
    return root


def ticket_store(cwd):
    """The directory holding this repo's tickets, or None if it has no store.

    Checks the current location first and the pre-CH-110 one second, so a repo
    that has not migrated still answers correctly. Returns None rather than a
    speculative path: "no store" is a real state that means "this repo is not
    ticket-driven", and a caller must be able to tell it from "store is empty".
    """
    root = repo_root(cwd) or cwd
    if not root:
        return None
    current = os.path.join(data_home(), DATA_SUBDIR,
                           os.path.basename(main_checkout(root)), STORE_SUBDIR)
    legacy = os.path.join(root, LEGACY_STORE)
    for path in (current, legacy):
        if os.path.isfile(os.path.join(path, "config.json")):
            return path
    return None
