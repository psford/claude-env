#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Verify correct dotnet process is serving.
Exit code 2 = hard block.
"""
import json, sys, re, os, glob, subprocess

TRIGGER = re.compile(r'localhost:\d+|http://127\.|open.*browser|curl.*localhost', re.IGNORECASE)

def run(args, timeout=5):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def get_worktree_root():
    rc, out, _ = run(["git", "rev-parse", "--show-toplevel"])
    return out if rc == 0 else None

def is_dotnet_project(root):
    return bool(glob.glob(os.path.join(root, "**", "*.csproj"), recursive=True)) if root else False

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = hook_input.get("tool_input", {}).get("command", "")
    if not TRIGGER.search(command):
        return 0

    root = get_worktree_root()
    if not root or not is_dotnet_project(root):
        return 0

    port_match = re.search(r'localhost:(\d+)', command, re.IGNORECASE)
    if not port_match:
        return 0
    port = port_match.group(1)

    try:
        rc, ss_out, _ = run(["ss", "-tlnp"])
        if rc != 0:
            return 0
        for line in ss_out.splitlines():
            if f":{port}" in line:
                pid_match = re.search(r'pid=(\d+)', line)
                if pid_match:
                    pid = pid_match.group(1)
                    try:
                        cwd = os.readlink(f"/proc/{pid}/cwd")
                        norm_cwd = os.path.realpath(cwd)
                        norm_root = os.path.realpath(root)
                        if not norm_cwd.startswith(norm_root):
                            print(f"BLOCKED: Wrong dotnet process serving on port {port}", file=sys.stderr)
                            print(f"  Serving from: {cwd}", file=sys.stderr)
                            print(f"  Expected:     {root}", file=sys.stderr)
                            print(f"\nFix: kill {pid} && cd {root}/src/RoadTripMap && dotnet run", file=sys.stderr)
                            return 2
                    except OSError:
                        pass
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
