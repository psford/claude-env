#!/usr/bin/env bash
# verify-bootstrap-structure.sh — Validates bootstrap.sh code structure without executing it.
#
# Usage:
#   bash scripts/verify-bootstrap-structure.sh [path/to/bootstrap.sh]
#
# Default target: bootstrap.sh at the repo root (relative to this script's location).
#
# This script checks structural properties of bootstrap.sh by static analysis only.
# It never runs bootstrap.sh or any of its dependencies.
#
# Exit codes:
#   0  All structural checks pass
#   1  One or more structural checks fail

set -euo pipefail

# ── Resolve target file ───────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ $# -ge 1 ]; then
  BOOTSTRAP="$1"
else
  BOOTSTRAP="${REPO_ROOT}/bootstrap.sh"
fi

# ── Color support ─────────────────────────────────────────────────────────────

if [ -t 1 ] && command -v tput &>/dev/null && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  GREEN=$(tput setaf 2)
  RED=$(tput setaf 1)
  YELLOW=$(tput setaf 3)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  GREEN=""
  RED=""
  YELLOW=""
  BOLD=""
  RESET=""
fi

# ── Result tracking ───────────────────────────────────────────────────────────

declare -a CHECK_NAMES=()
declare -a CHECK_RESULTS=()
declare -a CHECK_DETAILS=()
CRITICAL_FAIL=0

record() {
  local name="$1" status="$2" detail="${3:-}"
  CHECK_NAMES+=("$name")
  CHECK_RESULTS+=("$status")
  CHECK_DETAILS+=("$detail")
  if [ "$status" = "FAIL" ]; then
    CRITICAL_FAIL=1
  fi
}

# ── Preflight: confirm bootstrap.sh exists and is readable ───────────────────

echo "${BOLD}=== Bootstrap Structure Verification ===${RESET}"
echo "Target: ${BOOTSTRAP}"
echo ""

if [ ! -f "$BOOTSTRAP" ]; then
  echo "${RED}FAIL:${RESET} bootstrap.sh not found at ${BOOTSTRAP}"
  exit 1
fi

if [ ! -r "$BOOTSTRAP" ]; then
  echo "${RED}FAIL:${RESET} bootstrap.sh is not readable"
  exit 1
fi

# Helper: count pattern occurrences in bootstrap.sh
count_pattern() {
  grep -c "$1" "$BOOTSTRAP" 2>/dev/null || echo "0"
}

# Helper: check whether bootstrap.sh contains pattern
has_pattern() {
  grep -q "$1" "$BOOTSTRAP" 2>/dev/null
}

# ── Check 1: az login code path exists ───────────────────────────────────────
# The script must have a branch or function that invokes `az login`.

if has_pattern "az login\|az_login\|setup_azure_auth"; then
  # Further: confirm it's inside a conditional (not unconditional execution)
  az_line=$(grep -n "az login\|az_login\|setup_azure_auth" "$BOOTSTRAP" 2>/dev/null | head -1)
  record "az login code path exists" "PASS" "found: ${az_line}"
else
  record "az login code path exists" "FAIL" "no 'az login' invocation found in bootstrap.sh"
fi

# ── Check 2: 4+ git clone operations ─────────────────────────────────────────
# bootstrap.sh must clone at least 4 app repos.
# Accepts either: 4+ literal `git clone` calls, OR a single clone inside a loop
# over a repos array containing 4+ repo entries (the idiomatic pattern).

clone_count=$(count_pattern "git clone\|gh repo clone")
# Count repo entries in a repos array (psford/repo-name pattern)
repo_array_count=$(grep -c '"psford/\|"github\.com/psford/' "$BOOTSTRAP" 2>/dev/null || echo "0")

if [ "$clone_count" -ge 4 ]; then
  record "4+ git clone operations" "PASS" "${clone_count} clone operation(s)"
elif [ "$clone_count" -ge 1 ] && [ "$repo_array_count" -ge 4 ]; then
  record "4+ git clone operations" "PASS" "loop pattern: ${clone_count} clone in loop over ${repo_array_count} repo entries"
else
  record "4+ git clone operations" "FAIL" "${clone_count} clone call(s), ${repo_array_count} repo entries — need 4 repos cloned"
fi

# ── Check 3: pull-secrets.sh is referenced ───────────────────────────────────

if has_pattern "pull-secrets\|pull_secrets"; then
  ps_line=$(grep -n "pull-secrets\|pull_secrets" "$BOOTSTRAP" 2>/dev/null | head -1)
  record "pull-secrets.sh referenced" "PASS" "${ps_line}"
else
  record "pull-secrets.sh referenced" "FAIL" "pull-secrets.sh not referenced in bootstrap.sh"
fi

# ── Check 4: .NET install reference ──────────────────────────────────────────

if has_pattern "dotnet\|\.NET\|dotnet-sdk\|dotnet-runtime\|wsl-setup"; then
  dotnet_line=$(grep -n "dotnet\|\.NET\|dotnet-sdk\|wsl-setup" "$BOOTSTRAP" 2>/dev/null | head -1)
  record ".NET install reference" "PASS" "${dotnet_line}"
else
  record ".NET install reference" "FAIL" "no .NET install reference in bootstrap.sh"
fi

# ── Check 5: Python install reference ────────────────────────────────────────

if has_pattern "python\|pip\|wsl-setup"; then
  py_line=$(grep -n "python\|pip3\|wsl-setup" "$BOOTSTRAP" 2>/dev/null | head -1)
  record "Python install reference" "PASS" "${py_line}"
else
  record "Python install reference" "FAIL" "no Python install reference in bootstrap.sh"
fi

# ── Check 6: Node.js install reference ───────────────────────────────────────

if has_pattern "node\|nvm\|npm\|nodejs\|wsl-setup"; then
  node_line=$(grep -n "node\|nvm\|npm\|wsl-setup" "$BOOTSTRAP" 2>/dev/null | head -1)
  record "Node.js install reference" "PASS" "${node_line}"
else
  record "Node.js install reference" "FAIL" "no Node.js install reference in bootstrap.sh"
fi

# ── Check 7: Idempotency guards ───────────────────────────────────────────────
# The script must have some mechanism to skip already-completed steps.

idempotency_patterns="is_done\|mark_done\|BOOTSTRAP_STATE\|\.bootstrap-state\|grep.*done\|already.*done\|skip.*done"
idempotency_count=$(count_pattern "$idempotency_patterns")

if [ "$idempotency_count" -ge 2 ]; then
  record "Idempotency guards present" "PASS" "${idempotency_count} idempotency pattern(s)"
else
  record "Idempotency guards present" "FAIL" "found ${idempotency_count} idempotency pattern(s) — expected multiple (is_done/mark_done or similar)"
fi

# Confirm a state file or tracking mechanism is referenced
if has_pattern "BOOTSTRAP_STATE\|\.bootstrap-state\|\.bootstrap_state"; then
  state_line=$(grep -n "BOOTSTRAP_STATE\|\.bootstrap-state" "$BOOTSTRAP" 2>/dev/null | head -1)
  record "Idempotency state file referenced" "PASS" "${state_line}"
else
  record "Idempotency state file referenced" "FAIL" "no bootstrap state file variable found"
fi

# ── Check 8: pull-secrets.sh fetches from Key Vault and writes to .env ───────
# Inspect pull-secrets.sh (not bootstrap.sh) for Key Vault + .env output pattern.

PULL_SECRETS="${REPO_ROOT}/infrastructure/wsl/pull-secrets.sh"

if [ -f "$PULL_SECRETS" ]; then
  if grep -q "keyvault\|key.vault\|az keyvault" "$PULL_SECRETS" 2>/dev/null; then
    kv_line=$(grep -n "keyvault\|az keyvault" "$PULL_SECRETS" 2>/dev/null | head -1)
    record "pull-secrets.sh: Key Vault fetch" "PASS" "${kv_line}"
  else
    record "pull-secrets.sh: Key Vault fetch" "FAIL" "no Key Vault reference in pull-secrets.sh"
  fi

  if grep -q "\.env\|OUTPUT_PATH\|ENVEOF" "$PULL_SECRETS" 2>/dev/null; then
    env_line=$(grep -n "\.env\|OUTPUT_PATH" "$PULL_SECRETS" 2>/dev/null | head -1)
    record "pull-secrets.sh: writes to .env" "PASS" "${env_line}"
  else
    record "pull-secrets.sh: writes to .env" "FAIL" "no .env output in pull-secrets.sh"
  fi
else
  record "pull-secrets.sh: Key Vault fetch" "SKIP" "pull-secrets.sh not found at ${PULL_SECRETS}"
  record "pull-secrets.sh: writes to .env" "SKIP" "pull-secrets.sh not found"
fi

# ── Check 9: .env is gitignored ───────────────────────────────────────────────

GITIGNORE="${REPO_ROOT}/.gitignore"
if [ -f "$GITIGNORE" ]; then
  if grep -q "^\.env$\|^/\.env$\|^\.env " "$GITIGNORE" 2>/dev/null; then
    record ".env is gitignored" "PASS" "found .env entry in .gitignore"
  else
    record ".env is gitignored" "FAIL" ".env not in .gitignore — secrets would be committed"
  fi
else
  record ".env is gitignored" "FAIL" ".gitignore not found at ${REPO_ROOT}/.gitignore"
fi

# ── Check 10: bootstrap.sh is executable ─────────────────────────────────────

if [ -x "$BOOTSTRAP" ]; then
  record "bootstrap.sh is executable" "PASS" ""
else
  record "bootstrap.sh is executable" "FAIL" "chmod +x bootstrap.sh required"
fi

# ── Check 11: shebang is bash ─────────────────────────────────────────────────

first_line=$(head -1 "$BOOTSTRAP" 2>/dev/null || echo "")
if echo "$first_line" | grep -q "#!/.*bash\|#!/usr/bin/env bash"; then
  record "bootstrap.sh has bash shebang" "PASS" "${first_line}"
else
  record "bootstrap.sh has bash shebang" "FAIL" "shebang: '${first_line}'"
fi

# ── Check 12: set -euo pipefail ──────────────────────────────────────────────

if has_pattern "set -euo pipefail\|set -e\|set -eu"; then
  record "bootstrap.sh uses set -e (fail-fast)" "PASS" ""
else
  record "bootstrap.sh uses set -e (fail-fast)" "FAIL" "no 'set -e' or 'set -euo pipefail' found"
fi

# ── Summary table ─────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}=== Bootstrap Structure Summary ===${RESET}"
echo ""

MAX_NAME_LEN=0
for name in "${CHECK_NAMES[@]}"; do
  [ "${#name}" -gt "$MAX_NAME_LEN" ] && MAX_NAME_LEN=${#name}
done
[ "$MAX_NAME_LEN" -lt 5 ] && MAX_NAME_LEN=5

printf "%-${MAX_NAME_LEN}s   %-6s   %s\n" "CHECK" "STATUS" "DETAIL"
printf "%-${MAX_NAME_LEN}s   %-6s   %s\n" \
  "$(printf '─%.0s' $(seq 1 "$MAX_NAME_LEN"))" "──────" "──────────────────────"

for i in "${!CHECK_NAMES[@]}"; do
  name="${CHECK_NAMES[$i]}"
  status="${CHECK_RESULTS[$i]}"
  detail="${CHECK_DETAILS[$i]}"

  case "$status" in
    PASS) color="$GREEN" ;;
    FAIL) color="$RED" ;;
    SKIP) color="$YELLOW" ;;
    *)    color="" ;;
  esac

  printf "%-${MAX_NAME_LEN}s   ${color}%-6s${RESET}   %s\n" "$name" "$status" "$detail"
done

echo ""

pass_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^PASS$" || echo "0")
fail_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^FAIL$" || echo "0")
skip_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^SKIP$" || echo "0")
total_count=${#CHECK_NAMES[@]}

echo "PASS: ${pass_count}  FAIL: ${fail_count}  SKIP: ${skip_count}  TOTAL: ${total_count}"
echo ""

if [ "$CRITICAL_FAIL" -eq 1 ]; then
  echo "${RED}${BOLD}RESULT: One or more structural checks FAILED.${RESET}"
  exit 1
else
  echo "${GREEN}${BOLD}RESULT: All structural checks passed.${RESET}"
  exit 0
fi
