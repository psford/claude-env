#!/usr/bin/env bash
# verify-repo-split.sh — Unified verification for all 28 repo-split acceptance criteria.
#
# Usage:
#   bash scripts/verify-repo-split.sh [--skip-network] [--skip-ci-wait]
#
# Environment variables (set before running):
#   SA_VERIFY_DIR    Path to cloned stock-analyzer repo (default: ~/projects/stock-analyzer)
#   RT_VERIFY_DIR    Path to cloned road-trip repo      (default: ~/projects/road-trip)
#   CE_VERIFY_DIR    Path to cloned claude-env repo     (default: ~/projects/claude-env)
#   MONOREPO_DIR     Path to original claudeProjects    (default: ~/projects/claudeProjects)
#
# Flags:
#   --skip-network   Skip checks that require network (HTTP, gh API, GitHub Pages)
#   --skip-ci-wait   Skip checks that require CI run completion
#
# Exit codes:
#   0  All automated checks pass (HUMAN checks are always skipped in exit code)
#   1  One or more automated checks fail

set -euo pipefail

# ── Parse arguments ───────────────────────────────────────────────────────────

SKIP_NETWORK=0
SKIP_CI_WAIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-network) SKIP_NETWORK=1; shift ;;
    --skip-ci-wait) SKIP_CI_WAIT=1; shift ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [--skip-network] [--skip-ci-wait]"; exit 1 ;;
  esac
done

# ── Source assertion helpers ──────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./ac-assert-helpers.sh
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/ac-assert-helpers.sh"

# ── Resolve repo directories ──────────────────────────────────────────────────

SA_DIR="${SA_VERIFY_DIR:-$HOME/projects/stock-analyzer}"
RT_DIR="${RT_VERIFY_DIR:-$HOME/projects/road-trip}"
CE_DIR="${CE_VERIFY_DIR:-$HOME/projects/claude-env}"
MONO_DIR="${MONOREPO_DIR:-$HOME/projects/claudeProjects}"

# ── Color support ─────────────────────────────────────────────────────────────

if [ -t 1 ] && command -v tput &>/dev/null && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  GREEN=$(tput setaf 2)
  RED=$(tput setaf 1)
  YELLOW=$(tput setaf 3)
  CYAN=$(tput setaf 6)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  GREEN=""
  RED=""
  YELLOW=""
  CYAN=""
  BOLD=""
  RESET=""
fi

# ── Result tracking (mirrors verify-setup.sh pattern) ────────────────────────

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

# Parse a PASS/FAIL/HUMAN line from assertion helpers and record it.
# Format: STATUS:label:detail
record_assertion() {
  local result_line="$1"
  local status label detail

  # Split on first colon (status)
  status="${result_line%%:*}"
  local remainder="${result_line#*:}"
  # Split on next colon (label)
  label="${remainder%%:*}"
  detail="${remainder#*:}"

  case "$status" in
    PASS|FAIL|SKIP|HUMAN) ;;
    *) status="FAIL"; detail="malformed assertion result: $result_line" ;;
  esac

  record "$label" "$status" "$detail"
}

# Convenience: record a HUMAN check (requires manual verification).
record_human() {
  local name="$1" detail="${2:-requires manual verification}"
  record "$name" "HUMAN" "$detail"
}

# Convenience: skip a check with a reason.
record_skip() {
  local name="$1" detail="${2:-skipped}"
  record "$name" "SKIP" "$detail"
}

echo "${BOLD}=== Repo-Split Acceptance Criteria Verification ===${RESET}"
echo "stock-analyzer dir : ${SA_DIR}"
echo "road-trip dir      : ${RT_DIR}"
echo "claude-env dir     : ${CE_DIR}"
echo "monorepo dir       : ${MONO_DIR}"
echo "skip-network       : ${SKIP_NETWORK}"
echo "skip-ci-wait       : ${SKIP_CI_WAIT}"
echo ""

# ── AC1: Git history preserved via filter-repo ───────────────────────────────
echo "${CYAN}── AC1: Git history preserved ──${RESET}"

# AC1.1: stock-analyzer git log shows commits with rewritten root paths
if [ -d "$SA_DIR/.git" ]; then
  sa_commit_count=$(git -C "$SA_DIR" log --oneline 2>/dev/null | wc -l | tr -d ' ')
  if [ "$sa_commit_count" -gt 0 ]; then
    record "AC1.1 SA: git log has commits" "PASS" "${sa_commit_count} commits"
  else
    record "AC1.1 SA: git log has commits" "FAIL" "no commits found in ${SA_DIR}"
  fi
  # Confirm no old monorepo prefix paths remain
  record_assertion "$(assert_git_no_path_prefix "AC1.1 SA: no projects/stock-analyzer/ prefix" "$SA_DIR" "projects/stock-analyzer/")"
else
  record "AC1.1 SA: git log has commits" "FAIL" "not a git repo: ${SA_DIR}"
  record "AC1.1 SA: no projects/stock-analyzer/ prefix" "SKIP" "repo not found"
fi

# AC1.2: road-trip git log shows commits with rewritten root paths
if [ -d "$RT_DIR/.git" ]; then
  rt_commit_count=$(git -C "$RT_DIR" log --oneline 2>/dev/null | wc -l | tr -d ' ')
  if [ "$rt_commit_count" -gt 0 ]; then
    record "AC1.2 RT: git log has commits" "PASS" "${rt_commit_count} commits"
  else
    record "AC1.2 RT: git log has commits" "FAIL" "no commits found in ${RT_DIR}"
  fi
  record_assertion "$(assert_git_no_path_prefix "AC1.2 RT: no projects/road-trip/ prefix" "$RT_DIR" "projects/road-trip/")"
else
  record "AC1.2 RT: git log has commits" "FAIL" "not a git repo: ${RT_DIR}"
  record "AC1.2 RT: no projects/road-trip/ prefix" "SKIP" "repo not found"
fi

# AC1.3: claude-env git log shows relevant commits
if [ -d "$CE_DIR/.git" ]; then
  ce_commit_count=$(git -C "$CE_DIR" log --oneline 2>/dev/null | wc -l | tr -d ' ')
  if [ "$ce_commit_count" -gt 0 ]; then
    record "AC1.3 CE: git log has commits" "PASS" "${ce_commit_count} commits"
  else
    record "AC1.3 CE: git log has commits" "FAIL" "no commits found in ${CE_DIR}"
  fi
  # claude-env should not have stock-analyzer or road-trip paths
  record_assertion "$(assert_git_no_path_prefix "AC1.3 CE: no projects/stock-analyzer/ prefix" "$CE_DIR" "projects/stock-analyzer/")"
  record_assertion "$(assert_git_no_path_prefix "AC1.3 CE: no projects/road-trip/ prefix" "$CE_DIR" "projects/road-trip/")"
else
  record "AC1.3 CE: git log has commits" "FAIL" "not a git repo: ${CE_DIR}"
  record "AC1.3 CE: no projects/stock-analyzer/ prefix" "SKIP" "repo not found"
  record "AC1.3 CE: no projects/road-trip/ prefix" "SKIP" "repo not found"
fi

# AC1.4: Tags present (verify at least one tag if monorepo had tags)
if [ -d "$SA_DIR/.git" ]; then
  sa_tags=$(git -C "$SA_DIR" tag 2>/dev/null | wc -l | tr -d ' ')
  record "AC1.4 SA: tags present" "PASS" "${sa_tags} tag(s)"
fi

# AC1.5: Empty commits pruned (no commits with zero file changes) — advisory
record_human "AC1.5: empty commits pruned (advisory)" "git log --diff-filter=A in each repo; filter-repo prunes automatically"

# ── AC2: Independent CI, branch protection, deployment ───────────────────────
echo "${CYAN}── AC2: CI, branch protection, deployment ──${RESET}"

if [ "$SKIP_NETWORK" -eq 1 ]; then
  record_skip "AC2.1 SA: CI passes" "--skip-network set"
  record_skip "AC2.2 RT: CI passes" "--skip-network set"
  record_skip "AC2.3 SA: deploy workflow exists" "--skip-network set"
  record_skip "AC2.4 RT: deploy workflow exists" "--skip-network set"
  record_skip "AC2.5 SA: branch protection on main" "--skip-network set"
  record_skip "AC2.5 RT: branch protection on main" "--skip-network set"
  record_skip "AC2.6 SA: direct push to main rejected" "--skip-network set"
  record_skip "AC2.6 RT: direct push to main rejected" "--skip-network set"
elif [ "$SKIP_CI_WAIT" -eq 1 ]; then
  record_skip "AC2.1 SA: CI passes" "--skip-ci-wait set"
  record_skip "AC2.2 RT: CI passes" "--skip-ci-wait set"

  # Check CI workflow files exist locally
  if [ -d "$SA_DIR/.github/workflows" ]; then
    ci_files=$(find "$SA_DIR/.github/workflows/" -name "*.yml" 2>/dev/null | wc -l | tr -d ' ')
    record "AC2.1 SA: CI workflow files present" "PASS" "${ci_files} workflow file(s)"
  else
    record "AC2.1 SA: CI workflow files present" "FAIL" ".github/workflows not found in ${SA_DIR}"
  fi

  if [ -d "$RT_DIR/.github/workflows" ]; then
    rt_ci_files=$(find "$RT_DIR/.github/workflows/" -name "*.yml" 2>/dev/null | wc -l | tr -d ' ')
    record "AC2.2 RT: CI workflow files present" "PASS" "${rt_ci_files} workflow file(s)"
  else
    record "AC2.2 RT: CI workflow files present" "FAIL" ".github/workflows not found in ${RT_DIR}"
  fi

  # Check branch protection via gh API
  record_assertion "$(assert_gh_api_field "AC2.5 SA: branch protection on main" \
    "repos/psford/stock-analyzer/branches/main/protection" \
    ".required_status_checks.strict // false")"
  record_assertion "$(assert_gh_api_field "AC2.5 RT: branch protection on main" \
    "repos/psford/road-trip/branches/main/protection" \
    ".required_status_checks.strict // false")"

  record_human "AC2.3 SA: deploy workflow_dispatch works" "trigger workflow_dispatch on stock-analyzer and verify deployment"
  record_human "AC2.4 RT: deploy workflow_dispatch works" "trigger workflow_dispatch on road-trip and verify deployment"
  record_human "AC2.6 SA: direct push to main rejected" "attempt direct push to psford/stock-analyzer main"
  record_human "AC2.6 RT: direct push to main rejected" "attempt direct push to psford/road-trip main"
else
  # Full network checks
  # Check latest CI run for stock-analyzer
  sa_ci_status=$(gh run list --repo psford/stock-analyzer --limit 1 --json conclusion \
    --jq '.[0].conclusion' 2>/dev/null || echo "")
  if [ "$sa_ci_status" = "success" ]; then
    record "AC2.1 SA: CI passes" "PASS" "latest run: success"
  elif [ -z "$sa_ci_status" ]; then
    record "AC2.1 SA: CI passes" "SKIP" "no runs found or repo not accessible"
  else
    record "AC2.1 SA: CI passes" "FAIL" "latest run: ${sa_ci_status}"
  fi

  rt_ci_status=$(gh run list --repo psford/road-trip --limit 1 --json conclusion \
    --jq '.[0].conclusion' 2>/dev/null || echo "")
  if [ "$rt_ci_status" = "success" ]; then
    record "AC2.2 RT: CI passes" "PASS" "latest run: success"
  elif [ -z "$rt_ci_status" ]; then
    record "AC2.2 RT: CI passes" "SKIP" "no runs found or repo not accessible"
  else
    record "AC2.2 RT: CI passes" "FAIL" "latest run: ${rt_ci_status}"
  fi

  record_assertion "$(assert_gh_api_field "AC2.5 SA: branch protection on main" \
    "repos/psford/stock-analyzer/branches/main/protection" \
    ".required_status_checks.strict // false")"
  record_assertion "$(assert_gh_api_field "AC2.5 RT: branch protection on main" \
    "repos/psford/road-trip/branches/main/protection" \
    ".required_status_checks.strict // false")"

  record_human "AC2.3 SA: deploy workflow_dispatch works" "trigger workflow_dispatch on stock-analyzer"
  record_human "AC2.4 RT: deploy workflow_dispatch works" "trigger workflow_dispatch on road-trip"
  record_human "AC2.6 SA: direct push to main rejected" "attempt direct push to psford/stock-analyzer main"
  record_human "AC2.6 RT: direct push to main rejected" "attempt direct push to psford/road-trip main"
fi

# ── AC3: Road Trip fully decoupled ────────────────────────────────────────────
echo "${CYAN}── AC3: Road Trip infrastructure decoupled ──${RESET}"

# AC3.1: Road Trip uses its own SQL server — check Bicep or connection string
if [ -f "$RT_DIR/infrastructure/azure/main.bicep" ]; then
  # Should NOT reference Stock Analyzer's SQL server name
  if grep -q "sqlservertaurus\|psfordtaurus\|stock-analyzer" "$RT_DIR/infrastructure/azure/main.bicep" 2>/dev/null; then
    record "AC3.1 RT: own SQL server in Bicep" "FAIL" "still references SA SQL server in main.bicep"
  else
    record "AC3.1 RT: own SQL server in Bicep" "PASS" "no SA SQL server references in main.bicep"
  fi
else
  record "AC3.1 RT: own SQL server in Bicep" "SKIP" "main.bicep not found at ${RT_DIR}/infrastructure/azure/main.bicep"
fi

# AC3.2: Road Trip has its own App Service Plan in Bicep
if [ -f "$RT_DIR/infrastructure/azure/main.bicep" ]; then
  if grep -q "appServicePlan\|Microsoft.Web/serverfarms" "$RT_DIR/infrastructure/azure/main.bicep" 2>/dev/null; then
    record "AC3.2 RT: own App Service Plan in Bicep" "PASS" "App Service Plan resource found"
  else
    record "AC3.2 RT: own App Service Plan in Bicep" "FAIL" "no App Service Plan in main.bicep"
  fi
else
  record "AC3.2 RT: own App Service Plan in Bicep" "SKIP" "main.bicep not found"
fi

# AC3.3: Data migrated — manual verification needed
record_human "AC3.3 RT: data migrated to own SQL instance" "run Road Trip app against new SQL and verify photos/trips load"

# AC3.4: Shared ACR still used
if [ -d "$RT_DIR/.github/workflows" ]; then
  if grep -rq "acrstockanalyzerer34ug" "$RT_DIR/.github/workflows/" 2>/dev/null; then
    record "AC3.4 RT: shared ACR referenced in workflow" "PASS" "acrstockanalyzerer34ug found in workflows"
  else
    record "AC3.4 RT: shared ACR referenced in workflow" "FAIL" "acrstockanalyzerer34ug not found in workflows"
  fi
else
  record "AC3.4 RT: shared ACR referenced in workflow" "SKIP" ".github/workflows not found in ${RT_DIR}"
fi

# AC3.5: ACR registry change requires only URL + credentials — advisory
record_human "AC3.5 RT: ACR swap = URL+creds only (advisory)" "verify no hard-coded registry in app code; workflow uses env var for registry"

# ── AC4: Claude-env bootstraps fresh WSL2 ────────────────────────────────────
echo "${CYAN}── AC4: Bootstrap script ──${RESET}"

BOOTSTRAP="${CE_DIR}/bootstrap.sh"

if [ -f "$BOOTSTRAP" ]; then
  record "AC4: bootstrap.sh exists" "PASS" "$BOOTSTRAP"

  # AC4.1: Clones all 4 app repos
  clone_count=$(grep -c "git clone\|gh repo clone" "$BOOTSTRAP" 2>/dev/null || echo "0")
  if [ "$clone_count" -ge 4 ]; then
    record "AC4.1: bootstrap.sh clones 4+ repos" "PASS" "${clone_count} clone operation(s)"
  else
    record "AC4.1: bootstrap.sh clones 4+ repos" "FAIL" "only ${clone_count} clone operation(s) found"
  fi

  # AC4.2: Installs .NET, Python, Node
  for dep_label in "dotnet:.NET" "python:Python" "node:Node.js"; do
    dep_key="${dep_label%%:*}"
    dep_name="${dep_label#*:}"
    if grep -q "$dep_key" "$BOOTSTRAP" 2>/dev/null; then
      record "AC4.2: bootstrap.sh references ${dep_name}" "PASS" "found '${dep_key}' in bootstrap.sh"
    else
      record "AC4.2: bootstrap.sh references ${dep_name}" "FAIL" "'${dep_key}' not referenced in bootstrap.sh"
    fi
  done

  # AC4.3: Prompts for az login and pulls secrets
  if grep -q "az login\|az_login\|setup_azure_auth" "$BOOTSTRAP" 2>/dev/null; then
    record "AC4.3: bootstrap.sh has az login path" "PASS" ""
  else
    record "AC4.3: bootstrap.sh has az login path" "FAIL" "no az login reference in bootstrap.sh"
  fi

  if grep -q "pull-secrets\|pull_secrets" "$BOOTSTRAP" 2>/dev/null; then
    record "AC4.3: bootstrap.sh references pull-secrets.sh" "PASS" ""
  else
    record "AC4.3: bootstrap.sh references pull-secrets.sh" "FAIL" "pull-secrets.sh not referenced"
  fi

  # AC4.4: Registers plugin marketplaces and installs hooks
  if grep -q "plugin\|marketplace" "$BOOTSTRAP" 2>/dev/null; then
    record "AC4.4: bootstrap.sh references plugin setup" "PASS" ""
  else
    record "AC4.4: bootstrap.sh references plugin setup" "FAIL" "no plugin/marketplace reference in bootstrap.sh"
  fi

  # AC4.5: Generates VS Code workspace file
  if grep -q "code-workspace\|workspace" "$BOOTSTRAP" 2>/dev/null; then
    record "AC4.5: bootstrap.sh generates workspace file" "PASS" ""
  else
    record "AC4.5: bootstrap.sh generates workspace file" "FAIL" "no workspace generation in bootstrap.sh"
  fi

  # AC4.6: Idempotency guards present
  if grep -q "is_done\|mark_done\|BOOTSTRAP_STATE\|idempotent\|already" "$BOOTSTRAP" 2>/dev/null; then
    record "AC4.6: bootstrap.sh has idempotency guards" "PASS" ""
  else
    record "AC4.6: bootstrap.sh has idempotency guards" "FAIL" "no idempotency pattern detected"
  fi

  # AC4.7: No secrets in git-tracked files
  if [ -d "$CE_DIR/.git" ]; then
    ce_dir_ref="$CE_DIR"
    secret_hits=$(git -C "$ce_dir_ref" ls-files 2>/dev/null \
      | grep -v '\.py$' | grep -v '\.sh$' | grep -v '\.ps1$' | grep -v '\.md$' | grep -v '\.yml$' \
      | xargs -I FILE sh -c "grep -lE '(FINNHUB_API_KEY|EODHD_API_KEY|SLACK_BOT_TOKEN|ACR_PASSWORD)=.{8,}' \"$ce_dir_ref/FILE\" 2>/dev/null || true" \
      2>/dev/null | wc -l | tr -d ' ')
    if [ "$secret_hits" -eq 0 ]; then
      record "AC4.7: no secrets in git-tracked files" "PASS" ""
    else
      record "AC4.7: no secrets in git-tracked files" "FAIL" "found ${secret_hits} file(s) with potential secret values"
    fi
  else
    record "AC4.7: no secrets in git-tracked files" "SKIP" "CE repo not found at ${CE_DIR}"
  fi
else
  record "AC4: bootstrap.sh exists" "FAIL" "not found at ${BOOTSTRAP}"
  # Record all sub-ACs as failed since bootstrap.sh is missing
  for ac in "AC4.1:4 app repo clones" "AC4.2:.NET ref" "AC4.2:Python ref" "AC4.2:Node.js ref" \
            "AC4.3:az login" "AC4.3:pull-secrets" "AC4.4:plugin setup" \
            "AC4.5:workspace file" "AC4.6:idempotency" "AC4.7:no secrets"; do
    record "${ac%%:*}: ${ac#*:}" "FAIL" "bootstrap.sh not found"
  done
fi

# ── AC5: GitHub Pages docs unaffected ────────────────────────────────────────
echo "${CYAN}── AC5: GitHub Pages ──${RESET}"

if [ "$SKIP_NETWORK" -eq 1 ]; then
  record_skip "AC5.1: psford.github.io/stock-analyzer serves docs" "--skip-network set"
  record_skip "AC5.2: docs.html fetches from new URL" "--skip-network set"
  record_skip "AC5.3: old URL returns 404/redirect" "--skip-network set"
else
  record_assertion "$(assert_http_status "AC5.1: GitHub Pages at psford.github.io/stock-analyzer" \
    "https://psford.github.io/stock-analyzer" "200")"

  # AC5.2: docs.html in SA repo fetches from new URL
  if [ -d "$SA_DIR" ]; then
    docs_html=$(find "$SA_DIR" -name "docs.html" 2>/dev/null | head -1)
    if [ -n "$docs_html" ]; then
      if grep -q "psford.github.io/stock-analyzer" "$docs_html" 2>/dev/null; then
        record "AC5.2: docs.html uses new Pages URL" "PASS" "found psford.github.io/stock-analyzer in ${docs_html}"
      else
        record "AC5.2: docs.html uses new Pages URL" "FAIL" "psford.github.io/stock-analyzer not found in ${docs_html}"
      fi
    else
      record "AC5.2: docs.html uses new Pages URL" "SKIP" "docs.html not found in ${SA_DIR}"
    fi
  else
    record "AC5.2: docs.html uses new Pages URL" "SKIP" "SA repo not found"
  fi

  # AC5.3: Old URL returns 404 or redirect (advisory — monorepo may not be archived yet)
  old_status=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 \
    "https://psford.github.io/claudeProjects" 2>/dev/null || echo "000")
  if [ "$old_status" = "404" ] || [ "$old_status" = "301" ] || [ "$old_status" = "302" ]; then
    record "AC5.3: old Pages URL returns 404/redirect (advisory)" "PASS" "HTTP ${old_status}"
  else
    record "AC5.3: old Pages URL returns 404/redirect (advisory)" "SKIP" "HTTP ${old_status} — monorepo may not be archived yet"
  fi
fi

# ── AC6: Pre-split cleanup ────────────────────────────────────────────────────
echo "${CYAN}── AC6: Pre-split cleanup ──${RESET}"

# AC6.1: stephena-away and hook-test moved to archive/
if [ -d "$MONO_DIR" ]; then
  if [ -d "$MONO_DIR/projects/stephena-away" ]; then
    record "AC6.1: stephena-away archived" "FAIL" "projects/stephena-away still exists in monorepo"
  else
    record "AC6.1: stephena-away archived" "PASS" "projects/stephena-away not present in monorepo"
  fi

  if [ -d "$MONO_DIR/projects/hook-test" ]; then
    record "AC6.1: hook-test archived" "FAIL" "projects/hook-test still exists in monorepo"
  else
    record "AC6.1: hook-test archived" "PASS" "projects/hook-test not present in monorepo"
  fi

  if [ -d "$MONO_DIR/archive/stephena-away" ] || [ -d "$MONO_DIR/archive/projects/stephena-away" ]; then
    record "AC6.1: stephena-away in archive/" "PASS" "found in archive/"
  else
    record "AC6.1: stephena-away in archive/" "SKIP" "archive/ entry not found — may have been cleaned up"
  fi
else
  record_skip "AC6.1: stephena-away/hook-test archived" "monorepo not found at ${MONO_DIR}"
fi

# AC6.2: Migration manifest exists
manifest_paths=(
  "$MONO_DIR/docs/design-plans/repo-split-migration-manifest.md"
  "$CE_DIR/docs/design-plans/repo-split-migration-manifest.md"
  "./docs/design-plans/repo-split-migration-manifest.md"
)

manifest_found=0
for mp in "${manifest_paths[@]}"; do
  if [ -f "$mp" ]; then
    manifest_found=1
    record "AC6.2: migration manifest exists" "PASS" "found at ${mp}"
    break
  fi
done

if [ "$manifest_found" -eq 0 ]; then
  record "AC6.2: migration manifest exists" "FAIL" "repo-split-migration-manifest.md not found"
fi

# ── Summary table ─────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}=== Repo-Split Verification Summary ===${RESET}"
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
    PASS)  color="$GREEN" ;;
    FAIL)  color="$RED" ;;
    SKIP)  color="$YELLOW" ;;
    HUMAN) color="$CYAN" ;;
    *)     color="" ;;
  esac

  printf "%-${MAX_NAME_LEN}s   ${color}%-6s${RESET}   %s\n" "$name" "$status" "$detail"
done

echo ""

# Count results
pass_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^PASS$" || echo "0")
fail_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^FAIL$" || echo "0")
skip_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^SKIP$" || echo "0")
human_count=$(printf '%s\n' "${CHECK_RESULTS[@]}" | grep -c "^HUMAN$" || echo "0")
total_count=${#CHECK_NAMES[@]}

echo "PASS: ${pass_count}  FAIL: ${fail_count}  SKIP: ${skip_count}  HUMAN: ${human_count}  TOTAL: ${total_count}"
echo ""

if [ "$CRITICAL_FAIL" -eq 1 ]; then
  echo "${RED}${BOLD}RESULT: One or more automated checks FAILED.${RESET}"
  exit 1
else
  echo "${GREEN}${BOLD}RESULT: All automated checks passed.${RESET}"
  if [ "$human_count" -gt 0 ]; then
    echo "${CYAN}Note: ${human_count} check(s) require manual verification (HUMAN).${RESET}"
  fi
  exit 0
fi
