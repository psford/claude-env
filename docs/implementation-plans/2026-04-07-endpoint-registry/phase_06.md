# Endpoint Registry Implementation Plan

**Goal:** Create two enforcement hooks in claude-env that prevent regression: one blocks hardcoded connection strings/API keys in committed code, the other validates `endpoints.json` schema on commit.

**Architecture:** Both hooks follow the established claude-env pattern: Python scripts in `.claude/hooks/`, registered under `PreToolUse → Bash` in `settings.local.json`, receiving JSON via stdin, exiting 0 (allow) or 2 (block with stderr message). Hooks detect which repo they're in via `git rev-parse --show-toplevel` and only activate if `endpoints.json` exists at the repo root.

**Tech Stack:** Python 3.12 (standard library only — json, sys, re, subprocess, os)

**Scope:** 7 phases from original design (this is phase 6 of 7)

**Codebase verified:** 2026-04-07

---

## Acceptance Criteria Coverage

This phase implements and tests:

### endpoint-registry.AC1: Pointer file is single source of truth
- **endpoint-registry.AC1.4 Failure:** File containing an actual secret is rejected by schema validation

### endpoint-registry.AC5: Enforcement prevents regression
- **endpoint-registry.AC5.1 Success:** Pre-commit hook blocks hardcoded connection strings outside `endpoints.json`
- **endpoint-registry.AC5.2 Success:** Pre-commit hook validates `endpoints.json` schema on commit

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Create endpoint_registry_guard.py

**Verifies:** endpoint-registry.AC5.1

**Files:**
- Create: `/home/patrick/projects/claude-env/.claude/hooks/endpoint_registry_guard.py`

**Implementation:**

Create a pre-commit hook that blocks hardcoded connection strings and direct env var reads for known endpoint keys in staged files. Follow the established hook pattern from existing hooks like `workaround_guard.py` and `plan_api_url_guard.py`.

**Hook behavior:**
1. Read JSON from stdin — extract `tool_input.command`
2. Only activate on `git commit` commands (check if command contains `git commit`)
3. Get repo root via `git rev-parse --show-toplevel`
4. Check if `endpoints.json` exists at repo root — if not, exit 0 (hook doesn't apply to this repo)
5. Get staged file changes via `git diff --cached --unified=3 --diff-filter=ACM`
6. Skip `endpoints.json` itself (hardcoded values are expected there)
7. Scan added lines (lines starting with `+`, not `+++`) for these patterns:
   - Connection string patterns: `Server=`, `Data Source=`, `Initial Catalog=`, `database.windows.net`, `AccountName=`, `AccountKey=`, `DefaultEndpointsProtocol=`
   - Direct env var reads for known endpoint keys: `GetEnvironmentVariable("WSL_SQL_CONNECTION")`, `GetEnvironmentVariable("RT_DESIGN_CONNECTION")`, `GetEnvironmentVariable("NPS_API_KEY")`, `GetEnvironmentVariable("TWELVEDATA_API_KEY")`, `GetEnvironmentVariable("FMP_API_KEY")`, `GetEnvironmentVariable("FINNHUB_API_KEY")`, `GetEnvironmentVariable("EODHD_API_KEY")`, `GetEnvironmentVariable("MARKETAUX_API_TOKEN")`
   - appsettings connection string patterns: `config["ConnectionStrings`, `Configuration.GetConnectionString(`
8. If violations found: print descriptive error to stderr listing each file and line, exit 2
9. If no violations: exit 0

**Known env var keys to detect** (load from endpoints.json `env` source entries dynamically):
- Read endpoints.json, extract all `"key"` values from entries with `"source": "env"`
- Build regex pattern from these keys
- This makes the hook self-updating as new endpoints are added

**Exclusions:**
- `endpoints.json` itself
- `*.md` files (documentation may reference patterns)
- `test-endpoints.json` and files in test fixture directories
- Lines in comments (`//`, `#`, `<!--`)

```python
#!/usr/bin/env python3
"""Block hardcoded connection strings and direct env var reads for endpoint keys."""

import json
import os
import re
import subprocess
import sys


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git commit" not in command:
        return 0

    repo_root = get_repo_root()
    if not repo_root:
        return 0

    endpoints_path = os.path.join(repo_root, "endpoints.json")
    if not os.path.exists(endpoints_path):
        return 0  # No endpoints.json — hook doesn't apply

    # Load known env var keys from endpoints.json
    known_keys = load_env_keys(endpoints_path)

    # Get staged diff
    diff = get_staged_diff()
    if not diff:
        return 0

    violations = scan_diff(diff, known_keys)

    if violations:
        print("\n❌ ENDPOINT REGISTRY GUARD: Hardcoded connection/credential patterns found", file=sys.stderr)
        print("   Use EndpointRegistry.Resolve() instead of direct env var reads or hardcoded strings.\n", file=sys.stderr)
        for v in violations:
            print(f"   {v['file']}:{v['line']}: {v['reason']}", file=sys.stderr)
            print(f"      {v['content'].strip()}", file=sys.stderr)
        print(f"\n   {len(violations)} violation(s) found. Commit blocked.", file=sys.stderr)
        return 2

    return 0


def get_repo_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def load_env_keys(endpoints_path):
    """Extract env var key names from endpoints.json entries with source=env."""
    try:
        with open(endpoints_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = set()
        for env_name, env_block in data.get("environments", {}).items():
            for ep_name, ep_value in env_block.items():
                _extract_keys(ep_value, keys)
        return keys
    except Exception:
        return set()


def _extract_keys(obj, keys):
    if isinstance(obj, dict):
        if obj.get("source") == "env" and "key" in obj:
            keys.add(obj["key"])
        else:
            for v in obj.values():
                _extract_keys(v, keys)


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


# Connection string patterns (case-insensitive)
CONN_PATTERNS = [
    re.compile(r'Server\s*=\s*tcp:', re.IGNORECASE),
    re.compile(r'\.database\.windows\.net', re.IGNORECASE),
    re.compile(r'Initial\s+Catalog\s*=', re.IGNORECASE),
    re.compile(r'DefaultEndpointsProtocol\s*=', re.IGNORECASE),
    re.compile(r'AccountKey\s*=', re.IGNORECASE),
    re.compile(r'Configuration\.GetConnectionString\(', re.IGNORECASE),
    re.compile(r'config\["ConnectionStrings', re.IGNORECASE),
]

SKIP_EXTENSIONS = {".md", ".txt", ".json"}
SKIP_FILENAMES = {"endpoints.json", "test-endpoints.json", "endpoints.schema.json"}


def scan_diff(diff_text, known_keys):
    violations = []
    current_file = None
    line_num = 0

    # Build env var pattern from known keys
    if known_keys:
        env_pattern = re.compile(
            r'GetEnvironmentVariable\(\s*"(' + "|".join(re.escape(k) for k in known_keys) + r')"\s*\)'
        )
    else:
        env_pattern = None

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            current_file = None
        elif line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            # Parse line number from hunk header
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            line_num += 1
            if current_file and should_check(current_file):
                content = line[1:]  # Remove leading +

                # Skip comment lines
                stripped = content.strip()
                if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("<!--"):
                    continue

                # Check connection string patterns
                for pattern in CONN_PATTERNS:
                    if pattern.search(content):
                        violations.append({
                            "file": current_file,
                            "line": line_num,
                            "content": content,
                            "reason": "Hardcoded connection string pattern"
                        })
                        break

                # Check direct env var reads for known endpoint keys
                if env_pattern and env_pattern.search(content):
                    violations.append({
                        "file": current_file,
                        "line": line_num,
                        "content": content,
                        "reason": "Direct env var read for endpoint key — use EndpointRegistry.Resolve()"
                    })

    return violations


def should_check(filepath):
    filename = os.path.basename(filepath)
    if filename in SKIP_FILENAMES:
        return False
    _, ext = os.path.splitext(filename)
    if ext in SKIP_EXTENSIONS:
        return False
    if "/Fixtures/" in filepath or "/fixtures/" in filepath:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
```

**Verification:**

Test the hook locally by simulating a git commit with a hardcoded connection string:
```bash
cd /home/patrick/projects/claude-env
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | python .claude/hooks/endpoint_registry_guard.py
echo $?
```
Expected: Exit 0 (no endpoints.json in claude-env, so hook doesn't activate).

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create endpoint_schema_validator.py

**Verifies:** endpoint-registry.AC5.2, endpoint-registry.AC1.4

**Files:**
- Create: `/home/patrick/projects/claude-env/.claude/hooks/endpoint_schema_validator.py`

**Implementation:**

Create a pre-commit hook that validates `endpoints.json` against its schema when the file is being committed. Standard library only — no `jsonschema` package.

**Hook behavior:**
1. Read JSON from stdin — extract `tool_input.command`
2. Only activate on `git commit` commands
3. Get repo root, check for `endpoints.json`
4. Get staged files via `git diff --cached --name-only`
5. Only validate if `endpoints.json` is in the staged files (skip if not being modified)
6. Load `endpoints.json` and `endpoints.schema.json` from repo root
7. Validate structure manually (since we're standard-library-only):

**Validation checks:**
- Required top-level keys: `$schema`, `project`, `environments`
- Each environment block is an object
- Each endpoint entry has either `source` (simple) or sub-objects with `source` (compound)
- `literal` entries have `value`
- `env` entries have `key`
- `keyvault` entries have `vault` and `secret`
- No entry has a `value` that looks like a secret (connection strings, API key patterns in literal entries for prod environments)
- `source` values are one of: `literal`, `env`, `keyvault`

**Secret detection in literal values (AC1.4):**
- In `prod` environment blocks, flag `literal` entries whose `value` matches:
  - Connection string patterns (Server=, AccountKey=, etc.)
  - Long random-looking strings (>20 chars of alphanumeric — potential API keys)
  - Known secret prefixes (sk-, pk-, etc.)

```python
#!/usr/bin/env python3
"""Validate endpoints.json structure and reject files containing secrets."""

import json
import os
import re
import subprocess
import sys

VALID_SOURCES = {"literal", "env", "keyvault"}

SECRET_PATTERNS = [
    re.compile(r'Server\s*=.*Password\s*=', re.IGNORECASE),
    re.compile(r'AccountKey\s*=', re.IGNORECASE),
    re.compile(r'DefaultEndpointsProtocol\s*=', re.IGNORECASE),
    re.compile(r'^(sk|pk|rk|Bearer\s+)[A-Za-z0-9_\-]{20,}', re.IGNORECASE),
]

# Suspicious: long random strings that could be API keys (not URLs)
SUSPICIOUS_VALUE = re.compile(r'^[A-Za-z0-9_\-]{30,}$')


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return 0

    command = hook_input.get("tool_input", {}).get("command", "")
    if "git commit" not in command:
        return 0

    repo_root = get_repo_root()
    if not repo_root:
        return 0

    endpoints_path = os.path.join(repo_root, "endpoints.json")
    if not os.path.exists(endpoints_path):
        return 0

    # Only validate if endpoints.json is staged
    staged = get_staged_files()
    if "endpoints.json" not in staged:
        return 0

    errors = validate_endpoints(endpoints_path)

    if errors:
        print("\n❌ ENDPOINT SCHEMA VALIDATOR: endpoints.json validation failed", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        print(f"\n   {len(errors)} error(s) found. Commit blocked.", file=sys.stderr)
        return 2

    return 0


def get_repo_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5
        )
        return set(result.stdout.strip().split("\n")) if result.returncode == 0 else set()
    except Exception:
        return set()


def validate_endpoints(path):
    errors = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except Exception as e:
        return [f"Cannot read file: {e}"]

    # Required top-level keys
    for key in ("$schema", "project", "environments"):
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")

    if "environments" not in data:
        return errors

    envs = data["environments"]
    if not isinstance(envs, dict) or len(envs) == 0:
        errors.append("'environments' must be a non-empty object")
        return errors

    for env_name, env_block in envs.items():
        if not isinstance(env_block, dict):
            errors.append(f"Environment '{env_name}' must be an object")
            continue

        for ep_name, ep_value in env_block.items():
            ep_errors = validate_entry(ep_value, env_name, ep_name)
            errors.extend(ep_errors)

    return errors


def validate_entry(entry, env_name, ep_name, parent_path=""):
    """Validate a single endpoint entry (simple or compound)."""
    errors = []
    path = f"{parent_path}{ep_name}" if parent_path else f"{env_name}.{ep_name}"

    if not isinstance(entry, dict):
        errors.append(f"{path}: entry must be an object")
        return errors

    if "source" in entry:
        # Simple entry
        source = entry["source"]
        if source not in VALID_SOURCES:
            errors.append(f"{path}: invalid source '{source}' (must be one of: {', '.join(VALID_SOURCES)})")
            return errors

        if source == "literal":
            if "value" not in entry:
                errors.append(f"{path}: literal source missing 'value'")
            else:
                # Check for secrets in literal values (especially prod)
                value = entry["value"]
                if env_name == "prod":
                    for pattern in SECRET_PATTERNS:
                        if pattern.search(value):
                            errors.append(f"{path}: literal value in prod looks like a secret — use 'keyvault' source instead")
                            break
                    else:
                        if SUSPICIOUS_VALUE.match(value) and not value.startswith("http"):
                            errors.append(f"{path}: literal value in prod looks like an API key ({len(value)} chars) — use 'keyvault' source instead")

        elif source == "env":
            if "key" not in entry:
                errors.append(f"{path}: env source missing 'key'")

        elif source == "keyvault":
            if "vault" not in entry:
                errors.append(f"{path}: keyvault source missing 'vault'")
            if "secret" not in entry:
                errors.append(f"{path}: keyvault source missing 'secret'")

    else:
        # Compound entry — validate sub-entries
        has_sub = False
        for sub_name, sub_value in entry.items():
            if sub_name == "description":
                continue
            if isinstance(sub_value, dict) and "source" in sub_value:
                has_sub = True
                sub_errors = validate_entry(sub_value, env_name, sub_name, parent_path=f"{path}.")
                errors.extend(sub_errors)

        if not has_sub:
            errors.append(f"{path}: entry has no 'source' and no valid sub-entries")

    return errors


if __name__ == "__main__":
    sys.exit(main())
```

**Verification:**

Test with a valid endpoints.json:
```bash
cd /home/patrick/projects/claude-env
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | python .claude/hooks/endpoint_schema_validator.py
echo $?
```
Expected: Exit 0 (no endpoints.json in claude-env).

<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Register hooks in settings.local.json and commit

**Verifies:** endpoint-registry.AC5.1, endpoint-registry.AC5.2

**Files:**
- Modify: `/home/patrick/projects/claude-env/.claude/settings.local.json`

**Implementation:**

Add two new hook entries to the `PreToolUse` → `Bash` matcher block in `settings.local.json`. Add them alongside the existing hooks in the array.

```json
{
  "type": "command",
  "command": "python .claude/hooks/endpoint_registry_guard.py",
  "timeout": 10
},
{
  "type": "command",
  "command": "python .claude/hooks/endpoint_schema_validator.py",
  "timeout": 10
}
```

**Verification:**

Verify JSON is valid:
```bash
python -c "import json; json.load(open('/home/patrick/projects/claude-env/.claude/settings.local.json'))"
```
Expected: No errors.

**Commit:**

```bash
cd /home/patrick/projects/claude-env
git add .claude/hooks/endpoint_registry_guard.py .claude/hooks/endpoint_schema_validator.py .claude/settings.local.json
git commit -m "feat: add endpoint registry guard and schema validator hooks"
```

<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
