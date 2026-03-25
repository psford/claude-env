#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: JS module coverage guard.
Blocks commit of new JS source modules >50 LOC without test coverage.
Exit code 2 = hard block.
"""
import json, sys, re, subprocess

SOURCE_JS = re.compile(r'wwwroot/js/[^/]+\.js$', re.IGNORECASE)
MIN_LOC = 50

def run_git(*args, timeout=10):
    try:
        result = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=timeout)
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""

def stem(path):
    return re.sub(r'\.js$', '', path.split("/")[-1], flags=re.IGNORECASE)

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

    output = run_git("diff", "--cached", "--name-status", "--diff-filter=A")
    new_js = []
    for line in output.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and SOURCE_JS.search(parts[1]):
            new_js.append(parts[1])
    if not new_js:
        return 0

    violations = []
    for fpath in new_js:
        content = run_git("show", f":{fpath}")
        if not content:
            continue
        if re.search(r'//\s*NO-UNIT-TEST\s*:', content, re.IGNORECASE):
            continue
        loc = sum(1 for l in content.splitlines() if l.strip())
        if loc < MIN_LOC:
            continue

        mod = stem(fpath)
        repo_files = run_git("ls-files").strip().splitlines()
        staged = run_git("diff", "--cached", "--name-only").strip().splitlines()
        all_files = set(repo_files + staged)

        has_test = any(f.split("/")[-1].lower() in [f"{mod}.test.js", f"{mod}.spec.js"] for f in all_files)
        if has_test:
            continue

        test_files = [f for f in all_files if f.endswith(".spec.js") or f.endswith(".spec.ts")]
        pw_ref = False
        for tf in test_files:
            tc = run_git("show", f":{tf}")
            if not tc:
                try:
                    with open(tf) as fh:
                        tc = fh.read()
                except Exception:
                    continue
            if re.search(re.escape(mod), tc, re.IGNORECASE):
                pw_ref = True
                break
        if pw_ref:
            continue

        violations.append({"file": fpath, "loc": loc, "module": mod})

    if not violations:
        return 0
    print("BLOCKED: New JS module has no test coverage", file=sys.stderr)
    for v in violations:
        print(f"  {v['file']} ({v['loc']} non-blank lines, no {v['module']}.test.js or .spec.js)", file=sys.stderr)
    print("\nAdd a test file or annotate: // NO-UNIT-TEST: reason", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
