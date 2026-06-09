#!/usr/bin/env python3
"""
Phase preflight checker.

Usage:
  python helpers/phase_preflight.py <path-to-phase_NN.md>

Reads a fenced YAML block tagged ```prerequisites from the phase file
and validates the conditions before any task is started. Catches the
class of failure where a plan assumes git state, env vars, or installed
binaries that don't actually hold (e.g. phase 2 of photo-portfolio
visual-design hardcoded a branch name that was already merged).

Schema for the ```prerequisites block:

    branch:
      not_main: true            # current branch must not be main/master
      not_merged: true          # current branch must not be merged into main
      name_not: feat/old-name   # (optional) fail if current branch IS this name
    env:
      - REQUIRED_VAR_1          # list any env vars the phase depends on
      - REQUIRED_VAR_2
    binaries:
      - wrangler                # list any binaries the phase depends on
      - az
    pre_push_hook: true         # assert docs/hooks/pre-push exists
    playwright_installed: true  # assert ~/.cache/ms-playwright/ is populated

All fields are optional. A phase file without a prerequisites block is
flagged (exit 2) as a structural plan defect — the block IS the contract.

Exit codes:
  0  all preflight checks pass
  1  one or more preflight checks failed
  2  no prerequisites block found (structural defect)
"""

import os
import re
import shutil
import subprocess
import sys

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

PREREQ_FENCE = re.compile(r'```prerequisites\s*\n(.*?)\n```', re.DOTALL)


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def _current_branch():
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out if rc == 0 else "UNKNOWN"


def _is_merged_into_main(branch):
    for base in ("origin/main", "main"):
        rc, out = _run(["git", "branch", "--merged", base])
        if rc != 0:
            continue
        merged = {line.strip().lstrip("* ") for line in out.splitlines()}
        if branch in merged:
            return True
    return False


def _parse_prereqs(phase_path):
    with open(phase_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = PREREQ_FENCE.search(content)
    if not m:
        return None
    raw = m.group(1)
    if yaml is not None:
        return yaml.safe_load(raw) or {}
    # Minimal hand-parser (no yaml installed). Supports `key: value` and `- item`.
    result = {}
    current_key = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_key is not None:
            result.setdefault(current_key, []).append(stripped[2:].strip())
            continue
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            indent = len(line) - len(stripped)
            if indent == 0:
                current_key = k
                if v:
                    result[k] = _coerce_scalar(v)
                else:
                    result.setdefault(k, [])
            else:
                if isinstance(result.get(current_key), dict):
                    result[current_key][k] = _coerce_scalar(v) if v else None
                else:
                    result[current_key] = {k: _coerce_scalar(v) if v else None}
    return result


def _coerce_scalar(s):
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    return s


def _check_playwright():
    home = os.environ.get("HOME", "")
    candidates = [
        os.path.join(home, ".cache", "ms-playwright"),
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""),
    ]
    return any(c and os.path.isdir(c) and os.listdir(c) for c in candidates)


def _check_pre_push_hook(repo_root):
    candidates = [
        os.path.join(repo_root, "docs", "hooks", "pre-push"),
        os.path.join(repo_root, ".git", "hooks", "pre-push"),
        os.path.join(repo_root, ".claude", "hooks", "pre_push.py"),
    ]
    return any(os.path.exists(c) for c in candidates)


def main(argv):
    if len(argv) < 2:
        print("Usage: python helpers/phase_preflight.py <phase_NN.md>", file=sys.stderr)
        return 1

    phase_path = argv[1]
    if not os.path.exists(phase_path):
        print(f"ERROR: phase file not found: {phase_path}", file=sys.stderr)
        return 1

    prereqs = _parse_prereqs(phase_path)
    if prereqs is None:
        print(
            f"\n[phase_preflight] STRUCTURAL DEFECT: no ```prerequisites block in\n"
            f"  {phase_path}\n\n"
            f"Every phase plan must declare its preconditions in a fenced YAML block\n"
            f"so they can be validated before the executor starts. See:\n"
            f"  claude-env/infrastructure/plan-templates/phase.md.template\n",
            file=sys.stderr
        )
        return 2

    failures = []
    branch = _current_branch()

    branch_cfg = prereqs.get("branch") or {}
    if isinstance(branch_cfg, dict):
        if branch_cfg.get("not_main") and branch in ("main", "master"):
            failures.append(f"  [branch] current branch is '{branch}'; must not be main")
        if branch_cfg.get("not_merged") and _is_merged_into_main(branch):
            failures.append(f"  [branch] current branch '{branch}' is already merged into main")
        forbidden = branch_cfg.get("name_not")
        if forbidden and branch == forbidden:
            failures.append(f"  [branch] current branch must not be '{forbidden}'")

    for var in prereqs.get("env") or []:
        if not os.environ.get(var):
            failures.append(f"  [env]    {var} is not set")

    for binary in prereqs.get("binaries") or []:
        if not shutil.which(binary):
            failures.append(f"  [binary] '{binary}' not found in PATH")

    rc, repo_root = _run(["git", "rev-parse", "--show-toplevel"])
    if rc == 0 and prereqs.get("pre_push_hook"):
        if not _check_pre_push_hook(repo_root):
            failures.append("  [hook]   no pre-push hook found (docs/hooks/pre-push or .git/hooks/pre-push)")

    if prereqs.get("playwright_installed") and not _check_playwright():
        failures.append("  [playwright] browser binaries not found in ~/.cache/ms-playwright")

    if failures:
        print(f"\nPREFLIGHT FAILED for {os.path.basename(phase_path)} (branch: {branch})\n",
              file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        print("\nFix each item above before starting tasks in this phase.\n", file=sys.stderr)
        return 1

    print(f"[phase_preflight] OK — {os.path.basename(phase_path)} on branch '{branch}'")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
