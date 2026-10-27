#!/usr/bin/env python3
"""
Claude Code PostToolUse hook: what is actually in the camera's card folder.

flash_stamp_guard judges a command by its text, so a write into a repo's out/flash/ that no
command line names -- a script, a tool's own output path -- goes past it. This hook looks at
the folders themselves after every tool call that can write: every file in every
<projects>/*/out/flash/ must be bytes an emulator harness stamped (that repo's
firmware/c100/c/build/emulator-passed.json), or a file accepted, with exactly those bytes, in
claude-env's infrastructure/card-folders/card-folder-baseline.json. Anything else is named,
and the call is answered with a block -- after every call, until the file is gone or stamped.

The baseline is the folders' contents as they stood when this hook was added (2026-10-26),
accepted as they were. Changing it is a claude-env PR that Patrick merges, and
flash_stamp_guard refuses writes to the live copy.

<projects> is the directory claude-env sits in, found from this file's own location. No
variable, flag or file switches the watch off: a baseline or stamp file it can't read
accepts nothing.
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_ROOT = os.path.dirname(os.path.dirname(HERE))
PROJECTS = os.path.dirname(ENV_ROOT)
BASELINE = os.path.join(ENV_ROOT, "infrastructure", "card-folders", "card-folder-baseline.json")
STAMP_PARTS = ("firmware", "c100", "c", "build", "emulator-passed.json")
SHOWN = 20


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def card_folders():
    try:
        names = sorted(os.listdir(PROJECTS))
    except OSError:
        return []
    folders = (os.path.join(PROJECTS, n, "out", "flash") for n in names)
    return [f for f in folders if os.path.isdir(f)]


def unaccepted():
    """(card folder, relative path, sha256 or None) for every file neither stamped nor accepted."""
    baseline = read_json(BASELINE)
    folders = baseline.get("folders") if isinstance(baseline, dict) else None
    folders = folders if isinstance(folders, dict) else {}
    found = []
    for card in card_folders():
        repo = os.path.dirname(os.path.dirname(card))
        data = read_json(os.path.join(repo, *STAMP_PARTS))
        stamps = data.get("stamps") if isinstance(data, dict) else None
        stamps = set(stamps) if isinstance(stamps, dict) else set()
        accepted = folders.get(card)
        accepted = accepted if isinstance(accepted, dict) else {}
        for dirpath, dirnames, names in os.walk(card):
            dirnames.sort()
            for name in sorted(names):
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, card)
                digest = sha256(path)
                if digest is None or (digest not in stamps and accepted.get(rel) != digest):
                    found.append((card, rel, digest))
    return found


def main():
    try:
        json.load(sys.stdin)  # the payload doesn't matter: the folders are judged as they are
    except ValueError:
        pass
    found = unaccepted()
    if not found:
        return 0
    lines = [f"{os.path.relpath(card, PROJECTS)}/{rel} (sha256 {digest[:16] + '...' if digest else 'unreadable'})"
             for card, rel, digest in found[:SHOWN]]
    if len(found) > SHOWN:
        lines.append(f"... and {len(found) - SHOWN} more")
    print(json.dumps({
        "decision": "block",
        "reason": (
            "BLOCKED by card_folder_watch: the camera's card folder holds files no emulator harness "
            "stamped and the baseline doesn't accept:\n  " + "\n  ".join(lines) + "\n\n"
            "Remove each one (rm is allowed), or replace it with a build a harness stamped "
            "(ditherware: firmware/c100/c/emu_dsp_probe.py for the probes, emu_loader.py for the exif "
            "and fullres modules). A file the baseline should accept is a claude-env PR to "
            "infrastructure/card-folders/card-folder-baseline.json, which Patrick merges. This "
            "repeats after every tool call until the folder is clean."
        ),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
