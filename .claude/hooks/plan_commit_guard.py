#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block git push when plan docs are untracked.
Exit code 2 = hard block.
"""
import json, sys, re, subprocess

PLAN_DIRS = ["docs/implementation-plans", "docs/design-plans", "docs/test-plans"]

def run(args, timeout=10):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bpush\b', command, re.IGNORECASE):
        return 0

    rc, out, _ = run(["git", "status", "--porcelain", "--untracked-files=all"])
    if rc != 0 or not out:
        return 0

    untracked = []
    for line in out.splitlines():
        if len(line) < 3:
            continue
        xy, path = line[:2], line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[1]
        if not any(path.startswith(d + "/") for d in PLAN_DIRS):
            continue
        if xy[0] == "?" and xy[1] == "?":
            untracked.append(path)

    if not untracked:
        return 0

    print("BLOCKED: Plan documents are not committed.", file=sys.stderr)
    for f in untracked:
        print(f"  {f}", file=sys.stderr)
    print("\nCommit them before pushing:", file=sys.stderr)
    print(f"  git add {' '.join(untracked)}", file=sys.stderr)
    print('  git commit -m "docs: add plan documents"', file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
