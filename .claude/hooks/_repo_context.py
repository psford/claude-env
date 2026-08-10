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

STATEMENT_SPLIT = re.compile(r'&&|\|\||[;\n|]')
GIT_INVOCATION = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?:sudo\s+)?git\b')
QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')
# bash DELETES a backslash-newline before it parses anything -- it does not
# replace it with a space. The difference matters: `res\<newline>et` rejoins as
# `reset`, so substituting a space would split a keyword back apart and hand the
# guard a string bash never sees.
CONTINUATION = re.compile(r'\\\n')


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


def strip_heredoc_bodies(command):
    """Drop heredoc bodies before scanning. They are data, not commands.

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
        body_is_code = bool(FEEDS_CODE.match(line))
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
                "-c" in tokens or "-e" in tokens):
            kept.append(statement)
            continue
        masked = QUOTED.sub(lambda m: " " * len(m.group()), statement)
        kept.append(COMMENT.sub("", masked))
    return "\n".join(kept)


def target_directory(command, default=None):
    """The directory the git commands in `command` will run in.

    Honours a leading `cd <path>`, which applies to everything after it, and
    `git -C <path>`, which applies to one invocation and wins as the more
    specific. Unresolvable paths (a shell variable this cannot expand) fall
    back to `default`, which keeps the behaviour conservative rather than
    guessing.
    """
    cwd = default or os.getcwd()
    explicit = None

    def resolve(path, base):
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        return path if os.path.isdir(path) else None

    for statement in statements(command or ""):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            moved = resolve(tokens[1], cwd)
            if moved:
                cwd = moved
        if GIT_INVOCATION.match(statement) and "-C" in tokens:
            idx = tokens.index("-C")
            if idx + 1 < len(tokens):
                named = resolve(tokens[idx + 1], cwd)
                if named:
                    explicit = named

    return explicit or cwd


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
