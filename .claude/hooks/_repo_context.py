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
        body_is_code = scan_interpreter_bodies and bool(FEEDS_CODE.match(line))
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


ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

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
    return tuple(found), parsed


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
