#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: the camera's card folder takes only bytes the emulator passed.

Fires on Bash, Write, Edit, MultiEdit and NotebookEdit. A repo's out/flash/ holds what
Patrick puts on the camera's card. A file may land there only by `cp` (or `mv`) of bytes
whose sha256 is in the repo's firmware/c100/c/build/emulator-passed.json. The emulator
harnesses write that file themselves, at the end of a run in which every check passed
(ditherware: emu_dsp_probe.py for the probes, emu_loader.py for the exif and fullres
modules), and a run with any failure stamps nothing. Everything else that would write into
out/flash/ is refused, and so is anything that would write the stamp file. Reading either is
fine.

Why: on 2026-10-26 four probes in a row went to the camera with faults the checks hadn't
settled, and each cost Patrick a camera run. Rules written down didn't stop it; this does.

There is no way to switch it off: no variable, flag, token or file disables it, and a
command it can't read is refused. The scope is the card folder and the stamp file only:
a command that touches neither passes untouched.
"""

import hashlib
import json
import os
import re
import shlex
import sys

STAMP_PARTS = ("firmware", "c100", "c", "build", "emulator-passed.json")
STAMP_NAME = STAMP_PARTS[-1]
CARD = os.path.join("out", "flash")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# Commands that only read what they're given. git is here because out/ and build/ are
# ignored in ditherware, so git can't write either; a redirect is judged on its own.
READERS = {"ls", "cat", "head", "tail", "cmp", "diff", "sha256sum", "sha1sum", "md5sum", "stat", "file",
           "xxd", "hexdump", "od", "du", "wc", "grep", "jq", "test", "[", "echo", "printf", "git", "true"}
STRUCTURE = set("();&|\n")  # what ends or groups a command; a line break ends one as ";" does
REDIRECTS = {">", ">>", ">|", "&>", "&>>", "<>", ">&"}
INPUTS = {"<", "<<", "<<<", "<<-"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# cp/mv options that leave the bytes as they are. Anything else (recursion, links, a target
# directory given first) is refused rather than interpreted.
COPY_SHORT = set("finpuvT")
COPY_LONG = {"--force", "--interactive", "--no-clobber", "--preserve", "--update", "--verbose",
             "--no-target-directory"}
# What writes where it's pointed: after a cd the gate can't follow, these are refused.
BLIND_WRITERS = {"cp", "mv", "ln", "tee", "install", "rsync", "dd"}
NOT_CD = object()

HOW = ("The card folder (out/flash/) takes only a cp of bytes an emulator harness passed: run the "
       "harness that checks this build (ditherware: firmware/c100/c/emu_dsp_probe.py for the probes, "
       "emu_loader.py for the exif and fullres modules), then cp the build it stamped. A run with any "
       "failure stamps nothing.")


def card_root(path):
    """The repo root when path is in <repo>/out/flash (or is that folder), else None."""
    p = os.path.normpath(path)
    marker = os.sep + CARD
    i = p.find(marker + os.sep)
    if i < 0 and p.endswith(marker):
        i = len(p) - len(marker)
    return p[:i] if i >= 0 else None


def is_stamp(path):
    return os.path.basename(os.path.normpath(path)) == STAMP_NAME


def resolve(token, cwd):
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(token)))


def load_stamps(root):
    try:
        with open(os.path.join(root, *STAMP_PARTS), encoding="utf-8") as f:
            stamps = json.load(f)["stamps"]
        return set(stamps) if isinstance(stamps, dict) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def judge_copy(cmd, args, cwd):
    """A refusal for one cp/mv, or None when every file it puts in the card folder is stamped."""
    opts, operands, ended = [], [], False
    for a in args:
        if not ended and a == "--":
            ended = True
        elif not ended and a.startswith("-") and a != "-":
            opts.append(a)
        else:
            operands.append(a)
    for o in opts:
        known = o.split("=")[0] in COPY_LONG if o.startswith("--") else set(o[1:]) <= COPY_SHORT
        if not known:
            return f"{cmd} {o}: an option the gate doesn't take; stage one file at a time with {cmd} SOURCE DEST"
    if len(operands) < 2:
        return f"a {cmd} the gate can't read"
    *sources, dest = operands
    dest_abs = resolve(dest, cwd)
    into_dir = dest.endswith("/") or os.path.isdir(dest_abs) or len(sources) > 1
    for src in sources:
        target = os.path.join(dest_abs, os.path.basename(os.path.normpath(src))) if into_dir else dest_abs
        if is_stamp(target):
            return f"{cmd} onto the stamp file: only the emulator harness writes stamps"
        root = card_root(target)
        if root is None:
            continue
        stamps = load_stamps(root)
        if stamps is None:
            return f"no readable {os.path.join(*STAMP_PARTS)} in {root}: nothing has been stamped"
        digest = sha256(resolve(src, cwd))
        if digest is None:
            return f"can't read {src} to check its stamp"
        if digest not in stamps:
            return f"{src} (sha256 {digest[:16]}...) has no emulator pass stamp"
    return None


def tokenize(command):
    """shlex's words, with line breaks kept as separators and runs like ");" split apart.
    Raises ValueError for a command it can't read."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    out = []
    for t in lexer:
        if not (t and set(t) <= STRUCTURE):
            out.append(t)
            continue
        run = ""
        for ch in t:
            if ch in "()":
                out.extend([run, ch] if run else [ch])
                run = ""
            else:
                run += ch
        if run:
            out.append(run)
    return out


def is_structure(token):
    return bool(token) and set(token) <= STRUCTURE


def joins(sep):
    """How the next command depends on the one before: and (&&), or (||), pipe, bg (&), seq."""
    core = sep.strip("\n")
    if core == "&&":
        return "and"
    if core == "||":
        return "or"
    if "|" in core:
        return "pipe"
    return "bg" if core == "&" else "seq"


def cd_moves(seg, here):
    """NOT_CD for anything but cd/pushd/popd; else where it goes from each of `here`, or None
    when that's only known at run time."""
    args = list(seg)
    while args and ASSIGNMENT.match(args[0]):
        args = args[1:]
    cmd = os.path.basename(args[0]) if args else ""
    if cmd == "popd":
        return None
    if cmd not in ("cd", "pushd"):
        return NOT_CD
    rest = [a for a in args[1:] if not (a.startswith("-") and a != "-")]
    target = rest[0] if rest else "~"
    if here is None or target == "-" or "$" in target or "`" in target:
        return None
    return frozenset(resolve(target, c) for c in here)


def walk(tokens, cwd):
    """Each simple command with the directories it may run in, following cd as the shell
    does: after `cd X &&` only X; after `cd X;` X or, if the cd failed, where it was; after
    `||`, a pipe or `&`, where it was; a subshell's cd ends with it. None: a cd the gate
    can't follow."""
    here, stack, seg = frozenset([cwd]), [], []
    for t in tokens + [";"]:
        if not (t in ("(", ")") or is_structure(t)):
            seg.append(t)
            continue
        if seg:
            yield seg, here
            moved = cd_moves(seg, here)
            if moved is not NOT_CD and t not in ("(", ")"):
                if joins(t) == "and":
                    here = moved
                elif joins(t) == "seq":
                    here = None if moved is None or here is None else here | moved
            seg = []
        if t == "(":
            stack.append(here)
        elif t == ")" and stack:
            here = stack.pop()


def judge_lost(seg):
    """A refusal for a command whose directory the gate couldn't follow, when it writes."""
    args = [a for a in seg if not ASSIGNMENT.match(a)]
    if any(t in REDIRECTS for t in seg) or (args and os.path.basename(args[0]) in BLIND_WRITERS):
        return "a write after a cd the gate can't follow (a directory known only when the shell runs)"
    return None


def judge_segment(seg, cwd, cwd_in_card):
    """A refusal for one simple command, or None."""
    args, targets, i = [], [], 0
    while i < len(seg):
        t = seg[i]
        if t in REDIRECTS:
            if i + 1 < len(seg):
                targets.append(seg[i + 1])
            i += 2
        elif t in INPUTS:
            i += 2
        else:
            args.append(t)
            i += 1
    for t in targets:
        if is_stamp(t):
            return "a redirect into the stamp file: only the emulator harness writes stamps"
        if card_root(resolve(t, cwd)) is not None:
            return "a redirect into the card folder"
    while args and ASSIGNMENT.match(args[0]):
        args = args[1:]
    if not args:
        return None
    involved = cwd_in_card or any(card_root(resolve(a, cwd)) is not None or is_stamp(a) for a in args)
    if not involved:
        return None
    cmd = os.path.basename(args[0])
    if cmd in READERS or cmd in ("mkdir", "rm"):
        return None
    if cmd in ("cp", "mv"):
        return judge_copy(cmd, args[1:], cwd)
    return f"{cmd} touches the card folder or the stamp file, and only cp or mv of stamped bytes may write there"


def names_card(word):
    """A word with a path through a folder named flash: the card folder, or a way into it from
    a directory above. A name like flash_stamp_guard.py is not one."""
    return "flash" in word.split("/")


def judge_bash(command, cwd):
    try:
        tokens = tokenize(command)
    except ValueError:
        words = re.split(r"[\s'\"=()<>|;&]+", command)
        mentions = any(map(names_card, words)) or STAMP_NAME in command or card_root(cwd) is not None
        return "a command the gate can't read" if mentions else None
    steps = list(walk(tokens, cwd))
    places = {c for _, here in steps if here for c in here}
    mentions = (any(map(names_card, tokens)) or STAMP_NAME in command
                or any(card_root(c) is not None for c in places))
    if mentions and ("$" in command or "`" in command):
        return "a path built when the shell runs can't be checked now; give the paths as they are"
    if mentions and any(t.startswith("<<") for t in tokens):
        return "a heredoc that names the card folder or the stamp file; edit text files with Edit"
    for seg, here in steps:
        if here is None:
            refusal = judge_lost(seg)
        else:
            refusal = next(filter(None, (judge_segment(seg, c, card_root(c) is not None) for c in sorted(here))), None)
        if refusal:
            return refusal
    return None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    tool = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input") or {}
    cwd = hook_input.get("cwd") or os.getcwd()
    refusal = None
    if tool == "Bash":
        refusal = judge_bash(tool_input.get("command", ""), cwd)
    elif tool in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if path and is_stamp(path):
            refusal = f"{tool} on the stamp file: only the emulator harness writes stamps"
        elif path and card_root(resolve(path, cwd)) is not None:
            refusal = f"{tool} into the card folder"
    if refusal:
        print(f"BLOCKED: {refusal}. {HOW}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
