#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: CI cost guard.

Background: 2026-07-08 — a Claude instance submitted three needless iOS
builds to GitHub Actions within minutes, exhausting Patrick's entire
monthly Actions quota (macOS runners bill at a 10x minute multiplier).
Patrick's standing rulings (2026-07-09, both permanent):
  - FINAL WARNING: a repeat means the subscription is cancelled.
  - "you're never allowed to use github to test ios again."

What this hook does (Bash commands only):
1. Workflow-dispatch class — `gh workflow run`, `gh run rerun`,
   `gh api ...dispatches`, and `gh api .../runs/ID/rerun` (CH-237.10: a
   rerun re-bills a full macOS run, so the endpoint is in the class):
   - The repo is the one the COMMAND names: the `cd`/`git -C` target
     (CH-237.9), or gh's -R/--repo resolved against local checkouts'
     origin remotes (CH-237.10). A named repo that resolves to nothing
     on disk is refused — a repo this guard cannot inspect is not a repo
     it may approve.
   - If that repo's .github/workflows contains ANY macOS runner — inline,
     behind a matrix value, or as a block-list item (CH-237.10):
     UNCONDITIONAL BLOCK. No bypass token exists on purpose — this is
     the permanent iOS-on-GitHub ban. iOS builds run locally (Mac
     xcodebuild / the local CI runner).
   - Otherwise: BLOCK unless CI_RUN_OK=1 — exported in the shell that
     LAUNCHES Claude Code, which is the only place a hook can read it.
2. `git push` to a repo whose .github/workflows uses macOS runners a push
   can actually reach: BLOCK unless CI_MACOS_PUSH_OK=1 — likewise only
   readable from the launching shell, never from a command prefix.

Dispatches and pushes are found where they run, not only at the top of
the command (CH-237.10): inside shell payloads (`bash -c '...'`, eval),
behind wrappers (env, sudo, nice, nohup, xargs), and in heredoc bodies
fed to a shell — including after a `cd`.

Detection is deliberately conservative, and asks a different question on
each path. DISPATCH: any macOS runner in any workflow, however it is
spelled, because `gh workflow run` starts a job whatever its triggers
say. PUSH: only a macOS job in a workflow a push can actually reach —
anything unparseable counts as reachable. False negatives cost the
subscription, so everything unknown blocks.
"""

import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _repo_context import (  # noqa: E402,I001
    CODE_INTERPRETERS, FEEDS_CODE, HEREDOC_START, SHELLS,
    dispatches_a_workflow, parse_sees_everything, payload_of, statements,
    strip_wrappers, target_directory, workspace_repos,
)

DISPATCH_RE = re.compile(
    r'\bgh\s+workflow\s+run\b|\bgh\s+run\s+rerun\b'
    r'|\bgh\s+api\b[^|;&]*(?:dispatches|/rerun\b)',
    re.IGNORECASE,
)
PUSH_RE = re.compile(r'\bgit\b[^|;&]*\bpush\b')
ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*=')

# CH-237.10, defect 2: where a command's real verbs hide. argv0 stopped the
# old _kind at `bash`/`env`/`sudo`, so the dispatch behind them was never
# scanned and the raw-text fallback never fired (it only runs when NOTHING
# parsed — the statement list was full of tokens that merely failed to look
# like what they were).
#
# CE-2.20 moved SHELLS/CODE_INTERPRETERS/WRAPPERS and the walk itself into
# _repo_context, because deploy_guard needed the same answers and a second
# copy is how the two ended up disagreeing: the local list here never learned
# `timeout` or `ssh`, and the CSO gate found both dispatching silently.

# CH-237.10, defect 5: a macOS runner is not always spelled on the
# runs-on line. `runs-on: ${{ matrix.os }}` gets its runners from a matrix
# list elsewhere in the file, and a block list puts them on the NEXT lines.
# Both were invisible to `runs-on:.*macos` on BOTH the dispatch path and
# the push-reachability path.
RUNS_ON_LINE = re.compile(r'\bruns-on\s*:', re.IGNORECASE)
LIST_ITEM = re.compile(r'^[ \t]+-')
MATRIX_KEY = re.compile(r'matrix\.([A-Za-z_][A-Za-z0-9_-]*)')


def _text_has_macos(text):
    """True when any runner named in this workflow text is or may be macOS.

    Three shapes, one per pass over each runs-on line:
      - the value on the line itself (`runs-on: macos-15`)
      - a block list under it (`runs-on:\\n  - macos-15`)
      - a matrix reference resolved through its definitions anywhere in the
        file (`runs-on: ${{ matrix.os }}` + `os: [macos-15, ...]`)

    A matrix key with no definition in the file, and any other unresolvable
    `${{ ... }}` expression, count as macOS: a runner this guard cannot name
    is a runner it cannot clear, and "everything unknown blocks" is this
    file's standing rule. A matrix whose values all resolve linux-only is
    clean — the tightening must not become a blanket refusal (fixture 36).
    """
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if not RUNS_ON_LINE.search(line):
            continue
        value = line.split(":", 1)[1]
        j = idx + 1
        while j < len(lines) and LIST_ITEM.match(lines[j]):
            value += "\n" + lines[j]
            j += 1
        if "macos" in value.lower():
            return True
        m = MATRIX_KEY.search(value)
        if m:
            defs = re.findall(
                r'^[ \t]*' + re.escape(m.group(1)) + r'[ \t]*:(.*(?:\n[ \t]+-[^\n]*)*)',
                text, re.IGNORECASE | re.MULTILINE,
            )
            if not defs or any("macos" in d.lower() for d in defs):
                return True
            continue  # this line resolved macos-free; later lines still checked
        if "${{" in value:
            return True
    return False


def _strip_heredoc_bodies(command):
    """strip_heredoc_bodies with the feeder test CH-237.10 needed.

    Defect 3: _repo_context's FEEDS_CODE is anchored to the START of the
    feeder line, so

        cd <ios> && bash <<'EOF' ... gh workflow run ... EOF

    read as "a document fed to a cd" and the body was dropped as data. Real
    bash cds and then executes it. The test here is per STATEMENT of the
    feeder line — if any statement in it is an interpreter, the body is
    code. Everything else, including `cat <<EOF` writing a fixture that
    merely quotes a command (the CE-2.8 case), stays dropped as data.
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
        body_is_code = any(FEEDS_CODE.match(chunk) for chunk in statements(line))
        i += 1
        while i < len(lines) and lines[i].strip() != marker:
            if body_is_code:
                kept.append(lines[i])
            i += 1
        if i < len(lines):
            kept.append(lines[i])  # the terminator
        i += 1
    return "\n".join(kept)


def _repo_flag(tokens):
    """The [HOST/]OWNER/REPO gh was pointed at with -R/--repo, or None.

    Defect 1: nothing parsed this, so `gh workflow run -R owner/road-trip x`
    was judged against the session's directory — which routinely has no
    workflows — and approved without even asking for CI_RUN_OK. This is the
    realistic path: any session told to kick the iOS workflow.
    """
    for i, t in enumerate(tokens):
        if t in ("-R", "--repo"):
            return tokens[i + 1] if i + 1 < len(tokens) else ""
        if t.startswith("--repo="):
            return t.split("=", 1)[1]
    return None


def _classify(tokens, depth=0):
    """Yield (kind, inner_text, repo_spec) for every dispatch or push in one
    statement's tokens — including inside interpreter payloads and behind
    wrappers.

    This replaces CH-237.9's _kind and keeps its reason for reading TOKENS
    rather than the raw string (CE-2.8, third defect): the trigger phrase
    inside a quoted ARGUMENT fired the guard on real ticket text, twice.
    Quoted arguments stay inert here. An interpreter's payload is different
    — it is quoted AND it is code, and code gets parsed.

    inner_text is the payload a match was found in, so the payload's own
    `cd`/`git -C` are honoured when the target repo is resolved; None for a
    direct match. repo_spec is gh's -R/--repo value when one is present.

    The shell walk uses _repo_context's COMMAND_FLAG and FLAGS_TAKING_A_VALUE
    rather than a second copy: matching one spelling of `-c`/`-lc` is how
    two sibling parsers ended up with two opposite one-character bugs
    (CH-237.4), and reading an option's VALUE as the payload is the same
    bug family.

    Recursion needs no depth cap: every level consumes at least one token or
    descends into a strictly shorter string, so it terminates.
    """
    if not tokens:
        return
    argv, remote = strip_wrappers(tokens)
    if not argv:
        return
    argv0 = os.path.basename(argv[0])
    rest = argv[1:]

    if argv0 in SHELLS or argv0 in CODE_INTERPRETERS or argv0 == "eval":
        payload = payload_of(argv0, rest)
        if not payload:
            return
        if argv0 in SHELLS or argv0 == "eval":
            # Shell code: parse it exactly like the outer command. The whole
            # payload is carried as inner_text so a `cd` in an EARLIER chunk
            # of it still moves the target.
            for chunk in statements(payload):
                try:
                    sub = shlex.split(chunk)
                except ValueError:
                    continue
                while sub and ASSIGNMENT_RE.match(sub[0]):
                    sub = sub[1:]
                for kind, inner, spec, sub_remote in _classify(sub, depth + 1):
                    yield kind, inner or payload, spec, remote or sub_remote
        elif DISPATCH_RE.search(payload) or PUSH_RE.search(payload):
            # Python/ruby/node source is not shell, so token-parsing it would
            # be fiction. This is the same fail-closed raw-text fallback the
            # whole command gets when nothing parses, applied to the payload.
            kind = "dispatch" if DISPATCH_RE.search(payload) else "push"
            yield kind, payload, None, remote
        return

    if argv0 == "gh":
        if dispatches_a_workflow(argv):
            yield "dispatch", None, _repo_flag(rest), remote
        return

    if argv0 == "git" and "push" in rest:
        yield "push", None, None, remote


def _actions(command, session_cwd):
    """Yield (kind, directory, repo_spec) for every dispatch or push in
    `command`.

    CH-237.9. Two defects, one cause: this used to do its own splitting with
    `re.split(r'&&|\\|\\||;|\\|')` and to judge whatever repo the SESSION was
    started in.

    AC2 -- the private split never joined line continuations, and posix shlex
    does not either. bash DELETES a backslash-newline before parsing; shlex
    reads the backslash as an escape, so the newline survives and glues to
    the following word:

        gh \\<newline>workflow run ios.yml -> ['gh', '\\nworkflow', 'run', ...]
        git \\<newline>push origin main    -> ['git', '\\npush', 'origin', ...]

    Neither matched, and the raw-text fallback did not fire because it only
    runs when the statement list is EMPTY -- here it was full of tokens that
    merely failed to look like what they were. `statements()` joins
    continuations first, so adopting the shared parser is the whole fix, and it
    lands for every other guard in this repo at the same time.

    AC1 -- the repo is resolved PER STATEMENT, from the command's own `cd`
    and `git -C`, not from the session. The permanent macOS ban was previously
    chosen by whichever directory Claude Code happened to start in, so a
    dispatch reached an iOS repo untouched from any session that was not that
    repo. `target_directory` is given the command up to and including the
    statement being judged, because a `cd` earlier in the line applies to
    everything after it.

    CH-237.10 -- heredoc bodies fed to a shell are READ (defect 3, via the
    local _strip_heredoc_bodies above) and payloads/wrappers are classified
    (defect 2, in _classify). A dispatch carrying -R/--repo yields the named
    spec alongside its directory so the judge can refuse a repo that
    resolves to nothing on disk.

    Unparseable input falls back to the raw-text match against the session
    directory rather than to silence.
    """
    text = _strip_heredoc_bodies(command)
    prefix, parsed = [], 0
    for chunk in statements(text):
        prefix.append(chunk)
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            continue
        parsed += 1
        while tokens and ASSIGNMENT_RE.match(tokens[0]):
            tokens = tokens[1:]
        base = target_directory(" && ".join(prefix), default=session_cwd)
        for kind, inner, spec, remote in _classify(tokens):
            if remote:
                # It runs on another machine. Resolving it against this disk
                # would answer about the wrong box, so no directory is offered
                # and _judge refuses rather than guessing (CE-2.20).
                yield kind, None, spec, True
            elif spec is not None:
                yield kind, _resolve_named_repo(spec, base, session_cwd), spec, False
            else:
                d = target_directory(inner, default=base) if inner else base
                yield kind, d, None, False

    # `parsed` alone was the bug. It counted statements that TOKENISED, and a
    # subshell, an `if`, a `$(...)` or a quoted ssh payload all tokenise
    # perfectly while hiding the verb from the argv scan -- so the fail-closed
    # fallback never fired and thirteen real dispatches went silent that the
    # raw string match had refused (CE-2.20, found by QA 2026-09-11).
    if parsed and parse_sees_everything(command):
        return
    if DISPATCH_RE.search(command):  # not fully readable: fail closed
        yield "dispatch", session_cwd, None, False
    if PUSH_RE.search(command):
        yield "push", session_cwd, None, False


def _owner_repo(ref):
    """(owner, name) from any spelling of a repo reference, lowercase.

    Handles `acme/app`, `github.com/acme/app`, `https://github.com/acme/app`,
    `https://github.com/acme/app.git`, and `git@github.com:acme/app.git` —
    the last because origin URLs come back in ssh form more often than not.
    """
    ref = ref.strip()
    if ref.endswith(".git"):
        ref = ref[:-4]
    ref = re.sub(r'^[A-Za-z0-9+.\-]+://', '', ref)
    ref = re.sub(r'^[^/@]*@', '', ref)
    ref = ref.replace(":", "/")
    parts = [p for p in ref.split("/") if p]
    if len(parts) < 2:
        return None
    return parts[-2].lower(), parts[-1].lower()


def _resolve_named_repo(spec, base, session_cwd):
    """A local checkout whose origin is the repo `-R` named, or None.

    Resolution order: the repo the command already targets (a `cd`/`git -C`
    target whose origin matches IS the named repo), then every workspace
    repo — which is the sibling layout under ~/projects in production and
    honour CLAUDE_WORKSPACE_ROOTS when set. None means no checkout on this
    machine answers to that name, and the caller refuses: a repo this guard
    cannot open is a repo whose runners it cannot read.
    """
    want = _owner_repo(spec)
    if want is None:
        return None
    candidates = []
    root = _repo_root(base)
    if root:
        candidates.append(root)
    candidates.extend(workspace_repos(session_cwd))
    seen = set()
    for repo in candidates:
        if repo in seen:
            continue
        seen.add(repo)
        try:
            r = subprocess.run(
                ["git", "-C", repo, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5, check=False,
            )
        except Exception:  # noqa: BLE001 — an unreadable remote is skipped, not fatal
            continue
        if r.returncode == 0 and _owner_repo(r.stdout.strip()) == want:
            return repo
    return None


def _repo_root(cwd):
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=cwd, check=False,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001 — no repo root means dormant, never blocked
        return None


def _workflow_files(repo_root):
    wf_dir = os.path.join(repo_root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return []
    return [
        os.path.join(wf_dir, f)
        for f in os.listdir(wf_dir)
        if f.endswith((".yml", ".yaml"))
    ]


def _has_macos_runner(repo_root):
    """Any macOS runner anywhere. Still the right question for DISPATCH.

    `gh workflow run` starts a job regardless of what else could have started
    it, so triggers are irrelevant on that path and this stays a search over
    every workflow — in every spelling a runner takes (CH-237.10).
    """
    for path in _workflow_files(repo_root):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                if _text_has_macos(f.read()):
                    return True
        except OSError:
            continue
    return False


def _push_triggers(doc):
    """The trigger names in a parsed workflow, or None if they cannot be read.

    Two traps, both real rather than defensive:

    YAML 1.1 reads a bare `on:` key as the BOOLEAN True. So a perfectly valid
    workflow puts its triggers under `True`, and `doc["on"]` raises KeyError.
    Whether a repo is judged safe would otherwise depend on whether somebody
    quoted a key.

    And `on` takes three shapes -- `on: push` (str), `on: [push]` (list),
    `on:\n  push:` (dict). A reader handling one of them decides the other two
    have no push trigger, which ALLOWS a push it should refuse.
    """
    if not isinstance(doc, dict):
        return None
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {x for x in on if isinstance(x, str)}
    if isinstance(on, dict):
        return {k for k in on if isinstance(k, str)}
    return None


def _macos_reachable_from_push(repo_root):
    """Workflow files where a push can actually start a macOS job.

    CE-2.8. This used to be `_has_macos_runner` -- any `runs-on: macos` string
    in any file -- which blocked EVERY push to road-trip forever. Its only
    macOS workflow is dispatch-only, deliberately: Patrick, 2026-08-30, "the
    road trip ios app can only be developed on a mac, so it makes sense", and
    the standing ruling is that GitHub never builds iOS at all. So the guard
    was refusing real pushes to prevent a spend that could not occur, and the
    escape hatch it printed could not be used (it read os.environ while telling
    you to write the ack in the command).

    Anything unreadable counts as reachable. A parse failure means the triggers
    are unknown, and "no push trigger found, therefore safe" is how a gate
    becomes a bypass -- the same shape as a missing linter exiting 0.

    Out of scope, and blocking on purpose: a push-triggered macOS workflow with
    a `paths:` filter. Knowing whether the filter matches needs the diff, and
    erring toward refusal is the standing policy.
    """
    try:
        import yaml
    except ImportError:
        # No parser, so nothing can be known. Fall back to the old, blunter
        # question rather than to silence.
        return ["<all: pyyaml unavailable>"] if _has_macos_runner(repo_root) else []

    reachable = []
    for path in _workflow_files(repo_root):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        if not _text_has_macos(text):
            continue
        try:
            triggers = _push_triggers(yaml.safe_load(text))
        except Exception:  # noqa: BLE001 — anything unreadable must BLOCK, and
            # narrowing to YAMLError would let a surprising failure mode
            # (recursion, a bad tag, an encoding fault) escape as "no push
            # trigger found, therefore safe", which is the bypass shape.
            reachable.append(os.path.basename(path) + " (unparseable)")
            continue
        if triggers is None or "push" in triggers:
            reachable.append(os.path.basename(path))
    return reachable


def _judge(kind, directory, named=None, remote=False):
    """The exit code this one action earns in this one repo, or 0.

    The repo is named in every refusal. Since CH-237.9 it is resolved from the
    command rather than from the session, so "this repo" may well not be the
    one the terminal is sitting in, and a block that does not say which repo it
    means is a block nobody can act on. Since CH-237.10 a dispatch may name a
    repo with -R/--repo that no checkout answers to; that is refused here,
    because approving a repo whose workflows cannot be read is the false
    negative this guard exists to prevent.
    """
    if remote:
        # The minutes are GitHub's either way -- which machine holds the `gh`
        # client changes nothing about the bill. What it does change is that
        # this guard cannot read the target repo's workflows, and a repo it
        # cannot inspect is not a repo it may approve. Same rule as an
        # unresolvable -R below.
        print(
            "\n[ci_cost_guard] BLOCKED.\n"
            f"This command runs a {kind} on ANOTHER machine (via ssh), so this\n"
            "guard cannot read the workflows it would start — and metered minutes\n"
            "are billed to the same account wherever the client happens to sit.\n\n"
            "Run it from a local clone so the repo can be judged, or have Patrick\n"
            "run it from his own terminal.\n\n"
            "There is deliberately no bypass for this check.",
            file=sys.stderr,
        )
        return 2
    repo_root = _repo_root(directory) if directory else None
    if repo_root is None:
        if named:
            print(
                "\n[ci_cost_guard] BLOCKED.\n"
                f"The command names the repository {named} (-R/--repo), and no\n"
                "checkout on this machine resolves to it, so this guard cannot read\n"
                "that repo's workflows — and a repo it cannot inspect is not a repo\n"
                "it may approve. Run the command from inside a local clone (cd into\n"
                "it), or clone the repo into the workspace first.\n\n"
                "There is deliberately no bypass for this check.",
                file=sys.stderr,
            )
            return 2
        return 0
    has_workflows = bool(_workflow_files(repo_root))
    macos = _has_macos_runner(repo_root)
    where = os.path.basename(repo_root.rstrip("/")) or repo_root

    if kind == "dispatch":
        if macos:
            print(
                "\n[ci_cost_guard] BLOCKED — PERMANENTLY.\n"
                f"The workflows in {where} use macOS runners (10x minute billing), and\n"
                "Patrick's standing ruling (2026-07-09) is: GitHub is never used to\n"
                "test iOS again. There is deliberately NO bypass for this.\n\n"
                "Run iOS builds/tests locally: xcodebuild on the Mac, or the local\n"
                "CI runner (see feedback_metered_ci_discipline memory for status).",
                file=sys.stderr,
            )
            return 2
        if has_workflows and os.environ.get("CI_RUN_OK") != "1":
            # CH-237.10, the deadlock half: this refusal used to print
            # `CI_RUN_OK=1 <command>` while reading os.environ, and a hook
            # cannot see a per-command prefix — the instruction could not be
            # followed by anyone. The message now names what works. Reading
            # the prefix instead would make the ack an agent-usable token,
            # which is the bypass this guard is forbidden to grow (TNO).
            print(
                "\n[ci_cost_guard] BLOCKED.\n"
                "This command triggers a remote GitHub Actions run — metered minutes.\n"
                "A Claude instance exhausted the entire monthly quota on 2026-07-08;\n"
                "remote CI runs now require explicit human acknowledgment.\n\n"
                "Validate locally first. If the remote run is genuinely intended and\n"
                "Patrick has approved the spend, set CI_RUN_OK=1 in the shell that\n"
                "LAUNCHES Claude Code — not as a command prefix, which a hook cannot\n"
                "see (the same trap the push path documented in CE-2.8).",
                file=sys.stderr,
            )
            return 2
        return 0

    # git push path (CE-2.8: reachability, not any-macos-anywhere)
    reachable = _macos_reachable_from_push(repo_root)
    if reachable and os.environ.get("CI_MACOS_PUSH_OK") != "1":
        print(
            "\n[ci_cost_guard] BLOCKED.\n"
            f"A push to {where} can start a macOS job (10x minute billing):\n\n"
            "  " + "\n  ".join(reachable) + "\n\n"
            "That should not exist. Patrick's standing ruling (2026-07-09) is that\n"
            "GitHub never builds or tests iOS again, so a macOS job reachable from\n"
            "a push is the thing to fix, not to wave through:\n\n"
            "  - give that workflow a workflow_dispatch-only trigger, or\n"
            "  - drop the macOS job from it\n\n"
            "Either makes this push legal and costs nothing. Run the build locally\n"
            "instead (xcodebuild on the Mac, or the local CI runner).\n\n"
            "There is deliberately no in-command bypass. Patrick can override with\n"
            "CI_MACOS_PUSH_OK=1 exported in the shell that LAUNCHES Claude Code —\n"
            "not as a command prefix, which a hook cannot see.",
            file=sys.stderr,
        )
        return 2
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0

    cwd = data.get("cwd") or os.getcwd()
    for kind, directory, named, remote in _actions(command, cwd):
        verdict = _judge(kind, directory, named, remote)
        if verdict:
            return verdict
    return 0


if __name__ == "__main__":
    sys.exit(main())
