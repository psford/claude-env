#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Block cherry-picks of commits already on the current branch.
Exit code 2 = hard block.
"""
import json, sys, re, subprocess

def run(args, timeout=15, input_text=None):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input_text)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcherry-pick\b', command, re.IGNORECASE):
        return 0
    if re.search(r'--(?:abort|continue|quit|skip)', command, re.IGNORECASE):
        return 0

    rest = re.sub(r'\bgit\b\s+\bcherry-pick\b', '', command, flags=re.IGNORECASE).strip()
    refs = [t for t in rest.split() if not t.startswith('-')]
    if not refs:
        return 0

    incoming_pids = set()
    for ref in refs:
        if ".." in ref:
            rc, out, _ = run(["git", "rev-list", "--reverse", ref])
            shas = out.splitlines() if rc == 0 and out else []
        else:
            rc, sha, _ = run(["git", "rev-parse", "--verify", ref])
            shas = [sha] if rc == 0 and sha else []
        for sha in shas:
            rc, diff, _ = run(["git", "diff-tree", "-p", sha])
            if rc == 0 and diff:
                rc2, pid_out, _ = run(["git", "patch-id", "--stable"], input_text=diff)
                if rc2 == 0 and pid_out:
                    incoming_pids.add(pid_out.split()[0])

    if not incoming_pids:
        return 0

    rc, out, _ = run(["git", "rev-list", "origin/main..HEAD"])
    if rc != 0 or not out:
        return 0
    existing_pids = set()
    for sha in out.splitlines():
        rc, diff, _ = run(["git", "diff-tree", "-p", sha])
        if rc == 0 and diff:
            rc2, pid_out, _ = run(["git", "patch-id", "--stable"], input_text=diff)
            if rc2 == 0 and pid_out:
                existing_pids.add(pid_out.split()[0])

    dupes = incoming_pids & existing_pids
    if dupes:
        print(f"BLOCKED: {len(dupes)} patch(es) already exist on this branch.", file=sys.stderr)
        print(f"Cherry-picking would create duplicate commits.", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
