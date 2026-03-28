#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: Constant change test guard.
Blocks commit when a C# numeric constant changes but the test file isn't staged.
Exit code 2 = hard block.
"""
import json, sys, re, subprocess

CONST_CHANGE = re.compile(
    r'^\+\s*(?:private\s+|public\s+|internal\s+)?(?:static\s+)?const\s+'
    r'(?:int|long|double|float|decimal)\s+(\w+)\s*=\s*(\d+)',
    re.MULTILINE
)
CLASS_NAME = re.compile(r'(?:class|struct)\s+(\w+)', re.MULTILINE)

def run_git(*args, timeout=10):
    try:
        result = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=timeout)
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    if hook_input.get("tool_name") != "Bash":
        return 0
    command = hook_input.get("tool_input", {}).get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    output = run_git("diff", "--cached", "--name-status", "--diff-filter=AM")
    src_files = []
    for line in output.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[1].endswith(".cs") and "/Tests/" not in parts[1] and ".Tests/" not in parts[1]:
            src_files.append(parts[1])
    if not src_files:
        return 0

    staged_all = set(run_git("diff", "--cached", "--name-only").strip().splitlines())
    violations = []

    for fpath in src_files:
        diff = run_git("diff", "--cached", "--", fpath)
        if not diff:
            continue
        if re.search(r'//\s*CONSTANT-CHANGE-NO-TEST', diff, re.IGNORECASE):
            continue
        const_matches = CONST_CHANGE.findall(diff)
        if not const_matches:
            continue

        content = run_git("show", f":{fpath}")
        classes = CLASS_NAME.findall(content)
        class_name = classes[0] if classes else const_matches[0][0]

        all_files = run_git("ls-files").strip().splitlines()
        test_files = [f for f in all_files if f.endswith(".cs") and ("Tests" in f or "Spec" in f)]
        matching_tests = []
        pat = re.compile(re.escape(class_name), re.IGNORECASE)
        for tf in test_files:
            tc = run_git("show", f":{tf}")
            if tc and pat.search(tc):
                matching_tests.append(tf)

        staged_tests = [t for t in matching_tests if t in staged_all]
        if not staged_tests and matching_tests:
            for cn, val in const_matches:
                violations.append({"source": fpath, "const": cn, "value": val, "class": class_name, "tests": matching_tests})

    if not violations:
        return 0
    print("BLOCKED: Numeric constant changed — related tests not staged", file=sys.stderr)
    for v in violations:
        print(f"  {v['source']}: {v['class']}.{v['const']} = {v['value']}", file=sys.stderr)
        print(f"  Test file(s) not staged: {', '.join(v['tests'][:3])}", file=sys.stderr)
    print("\nStage the test file with updated values, or annotate: // CONSTANT-CHANGE-NO-TEST: reason", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
