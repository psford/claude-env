#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block git push when the current branch's PR is already merged/closed.
Exit code 2 = hard block.
"""
import json, sys, re, subprocess

def run(args, timeout=10):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def get_current_branch():
    rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out if rc == 0 and out and out != "HEAD" else None

def get_pr_state_for_branch(branch):
    rc, out, _ = run(["gh", "pr", "list", "--head", branch, "--base", "main", "--state", "all", "--json", "number,state", "--jq", '.[] | "\\(.number) \\(.state)"'])
    if rc != 0 or not out:
        return None, None, None
    open_pr = merged_pr = closed_pr = None
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            num, state = int(parts[0]), parts[1].upper()
            if state == "OPEN" and not open_pr: open_pr = num
            elif state == "MERGED" and not merged_pr: merged_pr = num
            elif state == "CLOSED" and not closed_pr: closed_pr = num
    return open_pr, merged_pr, closed_pr

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
    if re.search(r'--dry-run', command, re.IGNORECASE):
        return 0
    branch = get_current_branch()
    if not branch or branch in ("main", "develop", "HEAD"):
        return 0
    open_pr, merged_pr, closed_pr = get_pr_state_for_branch(branch)
    if open_pr:
        return 0
    dead_pr = merged_pr or closed_pr
    dead_state = "MERGED" if merged_pr else ("CLOSED" if closed_pr else None)
    if dead_pr and dead_state:
        # Allow sync pushes: branch even with main means no orphan risk
        rc, ahead, _ = run(["git", "rev-list", "--count", "origin/main..HEAD"])
        if rc == 0 and ahead == "0":
            return 0
        print(f"BLOCKED: Branch '{branch}' has a {dead_state} PR (#{dead_pr}) and no open PR.", file=sys.stderr)
        print(f"Pushing here would orphan commits — they will not reach main.", file=sys.stderr)
        print(f"\nOptions:", file=sys.stderr)
        print(f"  1. Create a new PR first:  gh pr create --base main --head {branch}", file=sys.stderr)
        print(f"  2. Switch to a new branch: git checkout -b <new-branch>", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
