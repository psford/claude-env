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
   `gh api ...dispatches`:
   - If the repo's .github/workflows contains ANY macOS runner:
     UNCONDITIONAL BLOCK. No bypass token exists on purpose — this is
     the permanent iOS-on-GitHub ban. iOS builds run locally (Mac
     xcodebuild / the local CI runner).
   - Otherwise: BLOCK unless CI_RUN_OK=1 (explicit, per-command human
     ack that a metered remote run is intended).
2. `git push` to a repo whose .github/workflows uses macOS runners:
   BLOCK unless CI_MACOS_PUSH_OK=1 — a push *triggers* those workflows,
   so shipping code to an iOS repo requires Patrick's explicit ack of
   the minute spend. Pushes to repos with only Linux runners (or no
   workflows) pass silently: normal development friction stays zero.

Detection is deliberately conservative, and asks a different question on
each path. DISPATCH: any `runs-on:` line mentioning macos, in any workflow,
because `gh workflow run` starts a job whatever its triggers say. PUSH: only
a macOS job in a workflow a push can actually reach — anything unparseable
counts as reachable. False negatives cost the subscription, so everything
unknown blocks.
"""

import json
import os
import re
import shlex
import subprocess
import sys

DISPATCH_RE = re.compile(
    r'\bgh\s+workflow\s+run\b|\bgh\s+run\s+rerun\b|\bgh\s+api\b[^|;&]*dispatches',
    re.IGNORECASE,
)
PUSH_RE = re.compile(r'\bgit\b[^|;&]*\bpush\b')
ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*=')
MACOS_RUNNER_RE = re.compile(r'runs-on\s*:.*mac[oO][sS]|runs-on\s*:.*\bmacos-', re.IGNORECASE)



def _statements(command):
    """The command split into statements, each as a shlex token list.

    CE-2.8, third defect. DISPATCH_RE and PUSH_RE match the RAW command, so the
    trigger phrase inside a quoted ARGUMENT fires the guard. Real, twice, while
    writing this ticket:

        ticket ac add CE-2.8 --text "...gh workflow run ..."   -> BLOCKED
        cat > fixture.md <<'EOF' ... COMMAND="gh workflow run"  -> BLOCKED

    Neither runs anything on GitHub. The first was a ticket description and the
    second a test fixture, and both were refused as attempts to spend money.

    A guard that fires on the mention of a thing rather than on the thing costs
    trust, which is the currency it needs to keep working: the way past a guard
    that cries wolf is to stop reading it. Same family as CH-192.2, where an
    unexpanded `$var` in a path made a guard judge the wrong repo -- both are
    the cost of reading a command as text instead of as a command.

    Unparseable input yields no statements, and the callers below fall back to
    the raw-text match rather than to silence.
    """
    out = []
    for part in re.split(r'&&|\|\||;|\|', command):
        try:
            tokens = shlex.split(part)
        except ValueError:
            continue
        while tokens and ASSIGNMENT_RE.match(tokens[0]):
            tokens = tokens[1:]
        if tokens:
            out.append(tokens)
    return out


def _is_dispatch(command):
    statements = _statements(command)
    if not statements:
        return bool(DISPATCH_RE.search(command))  # unparseable: fail closed
    for t in statements:
        if os.path.basename(t[0]) != "gh":
            continue
        rest = t[1:]
        if rest[:2] == ["workflow", "run"] or rest[:2] == ["run", "rerun"]:
            return True
        if rest[:1] == ["api"] and any("dispatches" in a for a in rest):
            return True
    return False


def _is_push(command):
    statements = _statements(command)
    if not statements:
        return bool(PUSH_RE.search(command))  # unparseable: fail closed
    return any(os.path.basename(t[0]) == "git" and "push" in t[1:]
               for t in statements)


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
    it, so triggers are irrelevant on that path and this stays a substring
    search over every workflow.
    """
    for path in _workflow_files(repo_root):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                if MACOS_RUNNER_RE.search(f.read()):
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
        if not MACOS_RUNNER_RE.search(text):
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

    is_dispatch = _is_dispatch(command)
    is_push = _is_push(command)
    if not (is_dispatch or is_push):
        return 0

    cwd = data.get("cwd") or os.getcwd()
    repo_root = _repo_root(cwd)
    if repo_root is None:
        return 0
    has_workflows = bool(_workflow_files(repo_root))
    macos = _has_macos_runner(repo_root)

    if is_dispatch:
        if macos:
            print(
                "\n[ci_cost_guard] BLOCKED — PERMANENTLY.\n"
                "This repo's workflows use macOS runners (10x minute billing), and\n"
                "Patrick's standing ruling (2026-07-09) is: GitHub is never used to\n"
                "test iOS again. There is deliberately NO bypass for this.\n\n"
                "Run iOS builds/tests locally: xcodebuild on the Mac, or the local\n"
                "CI runner (see feedback_metered_ci_discipline memory for status).",
                file=sys.stderr,
            )
            return 2
        if has_workflows and os.environ.get("CI_RUN_OK") != "1":
            print(
                "\n[ci_cost_guard] BLOCKED.\n"
                "This command triggers a remote GitHub Actions run — metered minutes.\n"
                "A Claude instance exhausted the entire monthly quota on 2026-07-08;\n"
                "remote CI runs now require explicit human acknowledgment.\n\n"
                "Validate locally first. If the remote run is genuinely intended and\n"
                "Patrick has approved the spend:  CI_RUN_OK=1 <command>",
                file=sys.stderr,
            )
            return 2
        return 0

    # git push path (CE-2.8: reachability, not any-macos-anywhere)
    reachable = _macos_reachable_from_push(repo_root)
    if reachable and os.environ.get("CI_MACOS_PUSH_OK") != "1":
        print(
            "\n[ci_cost_guard] BLOCKED.\n"
            "A push here can start a macOS job (10x minute billing):\n\n"
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


if __name__ == "__main__":
    sys.exit(main())
