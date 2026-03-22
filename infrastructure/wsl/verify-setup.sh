#!/usr/bin/env bash
set -euo pipefail

# WSL2 Claude Code Sandbox — Post-Setup Verification
# Runs every automatable acceptance criterion for the WSL2 environment.
# Usage: bash infrastructure/wsl/verify-setup.sh
#
# Exit 0 if all critical checks pass, exit 1 if any critical check fails.
# Non-critical failures are reported but do not cause a non-zero exit.

# ── Color support ─────────────────────────────────────────────────────────
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

# ── Result tracking ──────────────────────────────────────────────────────
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

# ── Resolve repo root ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "${BOLD}=== WSL2 Sandbox Verification ===${RESET}"
echo "Repo: $REPO_DIR"
echo ""

# ── 1. Toolchain version checks ──────────────────────────────────────────

# dotnet (must be 8.x)
if command -v dotnet &>/dev/null; then
  DOTNET_VER="$(dotnet --version 2>/dev/null || echo "")"
  if [[ "$DOTNET_VER" =~ ^8\. ]]; then
    record "dotnet 8.x" "PASS" "$DOTNET_VER"
  else
    record "dotnet 8.x" "FAIL" "got $DOTNET_VER"
  fi
else
  record "dotnet 8.x" "FAIL" "not installed"
fi

# python3
if command -v python3 &>/dev/null; then
  PY_VER="$(python3 --version 2>/dev/null | awk '{print $2}')"
  record "python3" "PASS" "$PY_VER"
else
  record "python3" "FAIL" "not installed"
fi

# node (must be 20.x)
if command -v node &>/dev/null; then
  NODE_VER="$(node --version 2>/dev/null || echo "")"
  if [[ "$NODE_VER" =~ ^v20\. ]]; then
    record "node 20.x" "PASS" "$NODE_VER"
  else
    record "node 20.x" "FAIL" "got $NODE_VER"
  fi
else
  record "node 20.x" "FAIL" "not installed"
fi

# npm
if command -v npm &>/dev/null; then
  NPM_VER="$(npm --version 2>/dev/null || echo "")"
  record "npm" "PASS" "$NPM_VER"
else
  record "npm" "FAIL" "not installed"
fi

# az
if command -v az &>/dev/null; then
  AZ_VER="$(az version --output tsv 2>/dev/null | head -1 || echo "installed")"
  record "az CLI" "PASS" "$AZ_VER"
else
  record "az CLI" "FAIL" "not installed"
fi

# git
if command -v git &>/dev/null; then
  GIT_VER="$(git --version 2>/dev/null | awk '{print $3}')"
  record "git" "PASS" "$GIT_VER"
else
  record "git" "FAIL" "not installed"
fi

# sqlcmd
SQLCMD_BIN=""
if command -v sqlcmd &>/dev/null; then
  SQLCMD_BIN="sqlcmd"
elif [ -x /opt/mssql-tools18/bin/sqlcmd ]; then
  SQLCMD_BIN="/opt/mssql-tools18/bin/sqlcmd"
elif [ -x /opt/mssql-tools/bin/sqlcmd ]; then
  SQLCMD_BIN="/opt/mssql-tools/bin/sqlcmd"
fi

if [ -n "$SQLCMD_BIN" ]; then
  record "sqlcmd" "PASS" "found at $SQLCMD_BIN"
else
  record "sqlcmd" "FAIL" "not installed"
fi

# claude
if command -v claude &>/dev/null; then
  CLAUDE_VER="$(claude --version 2>/dev/null || echo "installed")"
  record "claude CLI" "PASS" "$CLAUDE_VER"
else
  record "claude CLI" "FAIL" "not installed"
fi

# ── 2. .env completeness ─────────────────────────────────────────────────
ENV_FILE="$REPO_DIR/.env"
EXPECTED_KEYS=(
  FINNHUB_API_KEY
  SLACK_BOT_TOKEN
  SLACK_APP_TOKEN
  EODHD_API_KEY
  ANTHROPIC_API_KEY
  WSL_SQL_CONNECTION
  SA_DESIGN_CONNECTION
)

if [ -f "$ENV_FILE" ]; then
  ENV_MISSING=()
  ENV_EMPTY=()
  for key in "${EXPECTED_KEYS[@]}"; do
    # Check if key exists in .env
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
      # Check if value is non-empty
      val="$(grep "^${key}=" "$ENV_FILE" | head -1 | cut -d'=' -f2-)"
      if [ -z "$val" ]; then
        ENV_EMPTY+=("$key")
      fi
    else
      ENV_MISSING+=("$key")
    fi
  done

  if [ ${#ENV_MISSING[@]} -eq 0 ] && [ ${#ENV_EMPTY[@]} -eq 0 ]; then
    record ".env completeness" "PASS" "all ${#EXPECTED_KEYS[@]} keys present and non-empty"
  else
    problems=""
    if [ ${#ENV_MISSING[@]} -gt 0 ]; then
      problems="missing: ${ENV_MISSING[*]}"
    fi
    if [ ${#ENV_EMPTY[@]} -gt 0 ]; then
      [ -n "$problems" ] && problems="$problems; "
      problems="${problems}empty: ${ENV_EMPTY[*]}"
    fi
    record ".env completeness" "FAIL" "$problems"
  fi
else
  record ".env completeness" "FAIL" ".env file not found"
fi

# ── 3. Hook test ──────────────────────────────────────────────────────────
HOOK_SCRIPT="$REPO_DIR/.claude/hooks/session_start.py"
if [ -f "$HOOK_SCRIPT" ]; then
  # Run the hook with empty stdin. Exit 0 or 1 are both acceptable.
  # We only fail if there's a Python traceback (unhandled exception).
  HOOK_OUTPUT="$(python3 "$HOOK_SCRIPT" < /dev/null 2>&1 || true)"
  if echo "$HOOK_OUTPUT" | grep -q "Traceback (most recent call last)"; then
    record "hook: session_start" "FAIL" "Python traceback detected"
  else
    record "hook: session_start" "PASS" "no crash"
  fi
else
  record "hook: session_start" "SKIP" "script not found at $HOOK_SCRIPT"
fi

# ── 4. SQL TCP connectivity ──────────────────────────────────────────────
if [ -n "$SQLCMD_BIN" ]; then
  # Try to parse credentials from WSL_SQL_CONNECTION in .env
  SQL_CONN=""
  if [ -f "$ENV_FILE" ]; then
    SQL_CONN="$(grep "^WSL_SQL_CONNECTION=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2- || echo "")"
  fi

  if [ -n "$SQL_CONN" ]; then
    # Extract Server, User ID, Password from ADO.NET connection string
    SQL_SERVER="$(echo "$SQL_CONN" | grep -oP 'Server=\K[^;]+' || echo "")"
    SQL_USER="$(echo "$SQL_CONN" | grep -oP 'User Id=\K[^;]+' || echo "")"
    SQL_PASS="$(echo "$SQL_CONN" | grep -oP 'Password=\K[^;]+' || echo "")"

    if [ -n "$SQL_SERVER" ] && [ -n "$SQL_USER" ] && [ -n "$SQL_PASS" ]; then
      if $SQLCMD_BIN -S "$SQL_SERVER" -U "$SQL_USER" -P "$SQL_PASS" -Q "SELECT 1" -C -l 5 &>/dev/null; then
        record "SQL TCP connectivity" "PASS" "connected to $SQL_SERVER"
      else
        record "SQL TCP connectivity" "FAIL" "could not connect to $SQL_SERVER"
      fi
    else
      record "SQL TCP connectivity" "SKIP" "could not parse credentials from WSL_SQL_CONNECTION"
    fi
  else
    record "SQL TCP connectivity" "SKIP" "WSL_SQL_CONNECTION not set in .env"
  fi
else
  record "SQL TCP connectivity" "SKIP" "sqlcmd not installed"
fi

# ── 5. Git branch check ──────────────────────────────────────────────────
CURRENT_BRANCH="$(cd "$REPO_DIR" && git branch --show-current 2>/dev/null || echo "")"
if [ "$CURRENT_BRANCH" = "develop" ]; then
  record "git branch = develop" "PASS" ""
else
  record "git branch = develop" "FAIL" "on branch '$CURRENT_BRANCH'"
fi

# ── 6. .claude config directory ──────────────────────────────────────────
CLAUDE_DIR="$HOME/.claude"
if [ -d "$CLAUDE_DIR" ]; then
  if [ -d "$CLAUDE_DIR/.git" ]; then
    record ".claude config (git-backed)" "PASS" "$CLAUDE_DIR"
  else
    record ".claude config (git-backed)" "FAIL" "directory exists but not git-backed"
  fi
else
  record ".claude config (git-backed)" "FAIL" "directory not found"
fi

# ── 7. Solution build check (non-critical) ───────────────────────────────
# Note: claude-env contains no app code — individual app repos handle their own builds
CHECK_NAMES+=("dotnet build (non-critical)")
CHECK_RESULTS+=("SKIP")
CHECK_DETAILS+=("claude-env has no solution files; builds handled by individual app projects")

# ── 8. Windows path contamination in ~/.claude config ───────────────────
WIN_PATH_PATTERN='[A-Za-z]:\\'

INSTALLED_PLUGINS_FILE="$HOME/.claude/plugins/installed_plugins.json"
KNOWN_MARKETPLACES_FILE="$HOME/.claude/plugins/known_marketplaces.json"
CLAUDE_SETTINGS_FILE="$HOME/.claude/settings.json"

# Check installed_plugins.json for Windows paths (CRITICAL)
if [ -f "$INSTALLED_PLUGINS_FILE" ]; then
  WIN_MATCHES="$(grep -nP "$WIN_PATH_PATTERN" "$INSTALLED_PLUGINS_FILE" 2>/dev/null || true)"
  if [ -n "$WIN_MATCHES" ]; then
    record "plugin registry: no Windows paths" "FAIL" "Windows paths in installed_plugins.json — plugin loading will fail in WSL2"
  else
    record "plugin registry: no Windows paths" "PASS" "installed_plugins.json clean"
  fi
else
  CHECK_NAMES+=("plugin registry: no Windows paths")
  CHECK_RESULTS+=("SKIP")
  CHECK_DETAILS+=("installed_plugins.json not found")
fi

# Check known_marketplaces.json for Windows paths (CRITICAL)
if [ -f "$KNOWN_MARKETPLACES_FILE" ]; then
  WIN_MATCHES="$(grep -nP "$WIN_PATH_PATTERN" "$KNOWN_MARKETPLACES_FILE" 2>/dev/null || true)"
  if [ -n "$WIN_MATCHES" ]; then
    record "marketplace registry: no Windows paths" "FAIL" "Windows paths in known_marketplaces.json — marketplace will not resolve in WSL2"
  else
    record "marketplace registry: no Windows paths" "PASS" "known_marketplaces.json clean"
  fi
else
  CHECK_NAMES+=("marketplace registry: no Windows paths")
  CHECK_RESULTS+=("SKIP")
  CHECK_DETAILS+=("known_marketplaces.json not found")
fi

# Check settings.json for Windows paths (ADVISORY — does not set CRITICAL_FAIL)
if [ -f "$CLAUDE_SETTINGS_FILE" ]; then
  WIN_MATCHES="$(grep -nP "$WIN_PATH_PATTERN" "$CLAUDE_SETTINGS_FILE" 2>/dev/null || true)"
  if [ -n "$WIN_MATCHES" ]; then
    CHECK_NAMES+=("settings.json: no Windows paths (advisory)")
    CHECK_RESULTS+=("FAIL")
    CHECK_DETAILS+=("Windows paths detected — review hook paths for WSL2 compatibility")
    # Advisory: do not set CRITICAL_FAIL
  else
    CHECK_NAMES+=("settings.json: no Windows paths (advisory)")
    CHECK_RESULTS+=("PASS")
    CHECK_DETAILS+=("settings.json clean")
  fi
else
  CHECK_NAMES+=("settings.json: no Windows paths (advisory)")
  CHECK_RESULTS+=("SKIP")
  CHECK_DETAILS+=("settings.json not found")
fi

# Check that every installPath in installed_plugins.json actually exists on disk
if [ -f "$INSTALLED_PLUGINS_FILE" ] && command -v python3 &>/dev/null; then
  MISSING_PATHS="$(python3 - "$INSTALLED_PLUGINS_FILE" <<'PYEOF'
import sys, json, os

path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
except Exception as e:
    print(f"parse error: {e}")
    sys.exit(0)

# installed_plugins.json is a dict keyed by plugin name
missing = []
if isinstance(data, dict):
    for plugin_name, plugin_info in data.items():
        if isinstance(plugin_info, dict):
            install_path = plugin_info.get("installPath", "")
            if install_path and not os.path.isdir(install_path):
                missing.append(f"{plugin_name}: {install_path}")
        elif isinstance(plugin_info, str):
            # Some formats store the path directly as a string
            if plugin_info and not os.path.isdir(plugin_info):
                missing.append(f"{plugin_name}: {plugin_info}")
elif isinstance(data, list):
    for entry in data:
        if isinstance(entry, dict):
            install_path = entry.get("installPath", entry.get("path", ""))
            name = entry.get("name", entry.get("id", "unknown"))
            if install_path and not os.path.isdir(install_path):
                missing.append(f"{name}: {install_path}")

if missing:
    print("; ".join(missing))
PYEOF
  )"
  if [ -n "$MISSING_PATHS" ]; then
    record "plugin installPath dirs exist" "FAIL" "missing: $MISSING_PATHS"
  else
    record "plugin installPath dirs exist" "PASS" "all plugin directories present"
  fi
else
  CHECK_NAMES+=("plugin installPath dirs exist")
  CHECK_RESULTS+=("SKIP")
  CHECK_DETAILS+=("installed_plugins.json not found or python3 unavailable")
fi

# ── Summary table ─────────────────────────────────────────────────────────
echo ""
echo "${BOLD}=== Verification Summary ===${RESET}"
echo ""

# Calculate column width
MAX_NAME_LEN=0
for name in "${CHECK_NAMES[@]}"; do
  [ ${#name} -gt $MAX_NAME_LEN ] && MAX_NAME_LEN=${#name}
done
# Minimum width for header
[ $MAX_NAME_LEN -lt 5 ] && MAX_NAME_LEN=5

printf "%-${MAX_NAME_LEN}s   %-6s   %s\n" "CHECK" "STATUS" "DETAIL"
printf "%-${MAX_NAME_LEN}s   %-6s   %s\n" "$(printf '%0.s─' $(seq 1 $MAX_NAME_LEN))" "──────" "──────────────────────"

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

if [ $CRITICAL_FAIL -eq 1 ]; then
  echo "${RED}${BOLD}RESULT: One or more critical checks failed.${RESET}"
  exit 1
else
  echo "${GREEN}${BOLD}RESULT: All critical checks passed.${RESET}"
  exit 0
fi
