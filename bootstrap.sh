#!/usr/bin/env bash
set -euo pipefail

# Claude Env Bootstrap Script
# Creates a complete WSL2 development environment by cloning repos, installing dependencies,
# setting up Azure auth, plugins, hooks, and workspace configuration.
#
# Usage:
#   ./bootstrap.sh                    # Run with idempotency (skip already-done steps)
#   ./bootstrap.sh --force            # Force re-run all steps, bypass idempotency checks
#   ./bootstrap.sh --help             # Show this help message
#
# This script is idempotent and safe to run multiple times.

# ── Script Configuration ──────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_STATE="${SCRIPT_DIR}/.bootstrap-state"
FORCE_BOOTSTRAP="${FORCE_BOOTSTRAP:-0}"
PROJECTS_DIR="${PROJECTS_DIR:-$HOME/projects}"
SKIP_PROMPT="${SKIP_PROMPT:-0}"

# ── Color Output ──────────────────────────────────────────────────────────────

# Detect terminal color support
# shellcheck disable=SC2034
if [ -t 1 ] && command -v tput &>/dev/null && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  BLUE=$(tput setaf 4)
  GREEN=$(tput setaf 2)
  YELLOW=$(tput setaf 3)
  RED=$(tput setaf 1)
  RESET=$(tput sgr0)
else
  BLUE=""
  GREEN=""
  YELLOW=""
  RED=""
  RESET=""
fi

# ── Output Functions ──────────────────────────────────────────────────────────

info() {
  # shellcheck disable=SC2154
  echo "${BLUE}ℹ${RESET} $*"
}

success() {
  # shellcheck disable=SC2154
  echo "${GREEN}✓${RESET} $*"
}

warn() {
  # shellcheck disable=SC2154
  echo "${YELLOW}⚠${RESET} $*" >&2
}

error() {
  # shellcheck disable=SC2154
  echo "${RED}✗${RESET} $*" >&2
}

# ── Idempotency Pattern ───────────────────────────────────────────────────────

is_done() {
  if [ "$FORCE_BOOTSTRAP" -eq 1 ]; then
    return 1  # If --force, always return "not done"
  fi
  grep -qxF "$1" "$BOOTSTRAP_STATE" 2>/dev/null
}

mark_done() {
  echo "$1" >> "$BOOTSTRAP_STATE"
}

# ── Platform Detection ────────────────────────────────────────────────────────

is_wsl2() {
  [ -f /proc/version ] && grep -qi microsoft /proc/version
}

# ── Help ──────────────────────────────────────────────────────────────────────

show_help() {
  cat << 'EOF'
Claude Env Bootstrap Script

Usage:
  bootstrap.sh                   Run bootstrap with idempotency (skip already-done steps)
  bootstrap.sh --force           Force re-run all steps, bypassing idempotency checks
  bootstrap.sh --yes             Skip interactive prompts
  bootstrap.sh --help            Show this help message

This script:
- Clones all 4 app repositories to ~/projects/
- Installs dependencies (.NET 8, Python 3, Node.js, Azure CLI)
- Authenticates with Azure and pulls secrets to .env
- Registers plugin marketplaces and installs plugins
- Installs git hooks for the Claude Config repository
- Generates a VS Code workspace file for multi-repo development
- Verifies the complete setup

Environment variables:
  PROJECTS_DIR              Directory to clone repos into (default: ~/projects/)
  FORCE_BOOTSTRAP=1         Same as --force flag
  SKIP_PROMPT=1             Same as --yes flag

Requirements:
- Fresh or existing WSL2 Ubuntu 24.04+ environment
- Internet access for cloning repos and downloading packages
- Azure CLI authenticated (runs 'az login' if needed)

Platform detection:
- This script detects WSL2 environment and provides appropriate guidance

Examples:
  ./bootstrap.sh                        # First-time setup
  ./bootstrap.sh                        # Re-run is safe (idempotent)
  PROJECTS_DIR=/opt/dev ./bootstrap.sh  # Use custom projects directory
  ./bootstrap.sh --force                # Re-do all steps
  ./bootstrap.sh --yes                  # Non-interactive bootstrap
  FORCE_BOOTSTRAP=1 ./bootstrap.sh      # Use env var for force mode

EOF
}

# ── Step: clone_repos ────────────────────────────────────────────────────────

clone_repos() {
  local step_name="clone_repos"

  if is_done "$step_name"; then
    success "Repository cloning already done"
    return 0
  fi

  info "Cloning application repositories to $PROJECTS_DIR..."

  mkdir -p "$PROJECTS_DIR"

  # Array of repos to clone
  local repos=(
    "psford/stock-analyzer"
    "psford/road-trip"
    "psford/T-Tracker"
    "psford/SysTTS"
  )

  for repo in "${repos[@]}"; do
    local repo_name="${repo#*/}"  # Extract repo name after /
    local repo_dir="$PROJECTS_DIR/$repo_name"

    # Skip if already cloned
    if [ -d "$repo_dir" ] && [ -d "$repo_dir/.git" ]; then
      success "Repository already cloned: $repo_name"
      continue
    fi

    info "Cloning $repo..."
    if git clone "https://github.com/$repo.git" "$repo_dir" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
      if [ -d "$repo_dir/.git" ]; then
        success "Cloned $repo_name"
      else
        error "Clone succeeded but .git directory not found in $repo_dir"
        return 1
      fi
    else
      error "Failed to clone $repo"
      return 1
    fi
  done

  mark_done "$step_name"
  success "Repository cloning complete"
}

# ── Step: install_dependencies ───────────────────────────────────────────────

install_dependencies() {
  local step_name="install_dependencies"

  if is_done "$step_name"; then
    success "Dependency installation already done"
    return 0
  fi

  info "Installing dependencies via infrastructure/wsl/wsl-setup.sh..."

  local wsl_setup_script="${SCRIPT_DIR}/infrastructure/wsl/wsl-setup.sh"

  if [ ! -f "$wsl_setup_script" ]; then
    error "wsl-setup.sh not found at $wsl_setup_script"
    return 1
  fi

  if bash "$wsl_setup_script" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
    success "Dependencies installation via wsl-setup.sh complete"
  else
    error "wsl-setup.sh failed"
    return 1
  fi

  # Verify key tools after installation
  info "Verifying installed tools..."

  local tools_ok=1

  if command -v dotnet &>/dev/null; then
    local dotnet_ver
    dotnet_ver=$(dotnet --version 2>/dev/null || echo "unknown")
    success "dotnet $dotnet_ver"
  else
    warn "dotnet not found in PATH"
    tools_ok=0
  fi

  if command -v python3 &>/dev/null; then
    local py_ver
    py_ver=$(python3 --version 2>&1 | awk '{print $2}')
    success "python3 $py_ver"
  else
    warn "python3 not found in PATH"
    tools_ok=0
  fi

  if command -v node &>/dev/null; then
    local node_ver
    node_ver=$(node --version)
    success "node $node_ver"
  else
    warn "node not found in PATH"
    tools_ok=0
  fi

  if [ $tools_ok -eq 0 ]; then
    warn "Some tools are not available in PATH. This may be expected after first setup."
    warn "Try: source ~/.bashrc && source ~/.nvm/nvm.sh"
  fi

  mark_done "$step_name"
  success "Dependency installation complete"
}

# ── Step: setup_azure_auth ──────────────────────────────────────────────────

setup_azure_auth() {
  local step_name="setup_azure_auth"

  if is_done "$step_name"; then
    success "Azure auth setup already done"
    return 0
  fi

  info "Setting up Azure authentication..."

  # Check if already logged in
  if command -v az &>/dev/null && az account show &>/dev/null 2>&1; then
    success "Azure CLI already authenticated"
  else
    if ! command -v az &>/dev/null; then
      warn "Azure CLI not found in PATH. Install it first with wsl-setup.sh"
      return 1
    fi

    info "Azure CLI not authenticated. Opening login flow..."
    info "Please complete the browser login, then return to the terminal."
    info ""

    if az login; then
      success "Azure login successful"
    else
      error "Azure login failed"
      return 1
    fi
  fi

  # Pull secrets from Key Vault
  info "Pulling secrets from Azure Key Vault..."
  local pull_secrets_script="${SCRIPT_DIR}/infrastructure/wsl/pull-secrets.sh"

  if [ ! -f "$pull_secrets_script" ]; then
    error "pull-secrets.sh not found at $pull_secrets_script"
    return 1
  fi

  if bash "$pull_secrets_script" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
    success "Secrets pulled to .env"
  else
    error "pull-secrets.sh failed"
    return 1
  fi

  mark_done "$step_name"
  success "Azure auth setup complete"
}

# ── Step: setup_plugins ──────────────────────────────────────────────────────

setup_plugins() {
  local step_name="setup_plugins"

  if is_done "$step_name"; then
    success "Plugin setup already done"
    return 0
  fi

  info "Setting up Claude Code plugins..."

  if ! command -v claude &>/dev/null; then
    warn "Claude Code CLI not found. Install it first with wsl-setup.sh"
    return 0
  fi

  local claude_dir="$HOME/.claude"

  # Register marketplaces
  info "Registering plugin marketplaces..."

  local marketplace_dirs=(
    "$claude_dir/plugins/marketplaces/ed3d-plugins"
    "$claude_dir/plugins/marketplaces/patricks-local"
  )

  for marketplace_dir in "${marketplace_dirs[@]}"; do
    if [ ! -d "$marketplace_dir" ]; then
      warn "Marketplace not found: $marketplace_dir"
      continue
    fi

    local marketplace_name
    marketplace_name=$(basename "$marketplace_dir")

    # Check if already registered
    if [ -f "$claude_dir/plugins/known_marketplaces.json" ] && \
       grep -q "$marketplace_name" "$claude_dir/plugins/known_marketplaces.json" 2>/dev/null; then
      success "Marketplace already registered: $marketplace_name"
    else
      info "Registering marketplace: $marketplace_name"
      if claude plugin marketplace add "$marketplace_dir" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
        success "Registered marketplace: $marketplace_name"
      else
        warn "Failed to register marketplace: $marketplace_name"
      fi
    fi
  done

  # Install plugins from marketplaces
  info "Installing plugins from marketplaces..."

  if [ -f "$claude_dir/plugins/known_marketplaces.json" ]; then
    for marketplace_dir in "$claude_dir/plugins/marketplaces"/*/; do
      [ -d "$marketplace_dir" ] || continue

      local marketplace_name
      marketplace_name=$(basename "$marketplace_dir")

      # Find plugin subdirs in the marketplace
      for plugin_dir in "${marketplace_dir}plugins"/*/; do
        [ -d "$plugin_dir" ] || continue

        local plugin_name
        plugin_name=$(basename "$plugin_dir")
        local full_name="${plugin_name}@${marketplace_name}"

        # Check if already installed
        if [ -f "$claude_dir/plugins/installed_plugins.json" ] && \
           grep -q "$plugin_name" "$claude_dir/plugins/installed_plugins.json" 2>/dev/null; then
          success "Plugin already installed: $full_name"
        else
          info "Installing plugin: $full_name"
          if claude plugin install "$full_name" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
            success "Installed plugin: $full_name"
          else
            warn "Failed to install plugin: $full_name"
          fi
        fi
      done
    done
  fi

  # Install standalone hook plugins
  info "Installing hook plugins from claude-config..."

  local hook_plugins=(
    "psford-hook-session-checkpoint"
    "psford-hook-commit-gate"
    "psford-hook-playwright-gate"
    "psford-hook-security-guards"
    "psford-hook-agent-oversight"
  )

  for hook_plugin in "${hook_plugins[@]}"; do
    if [ -f "$claude_dir/plugins/installed_plugins.json" ] && \
       grep -q "$hook_plugin" "$claude_dir/plugins/installed_plugins.json" 2>/dev/null; then
      success "Hook plugin already installed: $hook_plugin"
    else
      info "Installing hook plugin: $hook_plugin"
      if claude plugin install "$hook_plugin" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
        success "Installed hook plugin: $hook_plugin"
      else
        warn "Failed to install hook plugin: $hook_plugin"
      fi
    fi
  done

  mark_done "$step_name"
  success "Plugin setup complete"
}

# ── Step: install_hooks ──────────────────────────────────────────────────────

install_hooks() {
  local step_name="install_hooks"

  if is_done "$step_name"; then
    success "Hook installation already done"
    return 0
  fi

  info "Installing Claude Config git hooks..."

  local hooks_installer="${SCRIPT_DIR}/infrastructure/wsl/install-claude-config-hooks.sh"

  if [ ! -f "$hooks_installer" ]; then
    error "install-claude-config-hooks.sh not found at $hooks_installer"
    return 1
  fi

  if bash "$hooks_installer" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
    success "Claude Config hooks installed"
  else
    error "Failed to install hooks"
    return 1
  fi

  # Ensure app repo hooks directories exist
  info "Ensuring app repository hooks directories exist..."

  for repo_name in stock-analyzer road-trip T-Tracker SysTTS; do
    local repo_dir="$PROJECTS_DIR/$repo_name"
    if [ -d "$repo_dir" ]; then
      mkdir -p "$repo_dir/.claude/hooks"
      success "Ensured hooks directory: $repo_dir/.claude/hooks"
    fi
  done

  mark_done "$step_name"
  success "Hook installation complete"
}

# ── Step: generate_workspace ─────────────────────────────────────────────────

generate_workspace() {
  local step_name="generate_workspace"

  if is_done "$step_name"; then
    success "Workspace generation already done"
    return 0
  fi

  info "Generating VS Code workspace file..."

  local workspace_file="$PROJECTS_DIR/dev-workspace.code-workspace"

  cat > "$workspace_file" << 'WORKSPACE_EOF'
{
  "folders": [
    {
      "path": "claude-env",
      "name": "Claude Env"
    },
    {
      "path": "stock-analyzer",
      "name": "Stock Analyzer"
    },
    {
      "path": "road-trip",
      "name": "Road Trip"
    },
    {
      "path": "T-Tracker",
      "name": "T-Tracker"
    },
    {
      "path": "SysTTS",
      "name": "SysTTS"
    }
  ],
  "settings": {}
}
WORKSPACE_EOF

  if [ -f "$workspace_file" ]; then
    success "Generated workspace file: $workspace_file"
    info "Open in VS Code: code $workspace_file"
  else
    error "Failed to create workspace file"
    return 1
  fi

  mark_done "$step_name"
  success "Workspace generation complete"
}

# ── Step: verify_bootstrap ───────────────────────────────────────────────────

verify_bootstrap() {
  local step_name="verify_bootstrap"

  if is_done "$step_name"; then
    success "Bootstrap verification already done"
    return 0
  fi

  info "Running comprehensive bootstrap verification..."

  local verify_script="${SCRIPT_DIR}/infrastructure/wsl/verify-setup.sh"

  if [ ! -f "$verify_script" ]; then
    warn "verify-setup.sh not found at $verify_script, skipping comprehensive checks"
  else
    info "Running verify-setup.sh..."
    if bash "$verify_script" 2>&1 | tee -a "$BOOTSTRAP_STATE.log"; then
      success "verify-setup.sh passed"
    else
      warn "verify-setup.sh reported issues"
    fi
  fi

  # Additional bootstrap-specific checks
  info "Running bootstrap-specific checks..."

  local check_pass=1

  # Check repos exist
  for repo_name in stock-analyzer road-trip T-Tracker SysTTS; do
    local repo_dir="$PROJECTS_DIR/$repo_name"
    if [ -d "$repo_dir" ] && [ -d "$repo_dir/.git" ]; then
      success "Repository exists: $repo_name"
    else
      error "Repository missing or not a git repo: $repo_name"
      check_pass=0
    fi
  done

  # Check .env exists and is not empty
  local env_file="$SCRIPT_DIR/.env"
  if [ -f "$env_file" ] && [ -s "$env_file" ]; then
    success ".env file exists and is not empty"
  else
    warn ".env file missing or empty"
    check_pass=0
  fi

  # Check .env is gitignored
  if command -v git &>/dev/null && git check-ignore "$env_file" &>/dev/null 2>&1; then
    success ".env is gitignored"
  else
    warn ".env may not be properly gitignored"
  fi

  # Check no secrets in git-tracked files (sample check)
  info "Checking for accidentally committed secrets..."
  if git ls-files 2>/dev/null | xargs grep -l "FINNHUB_API_KEY\|EODHD_API_KEY\|SLACK_BOT_TOKEN" 2>/dev/null; then
    error "SECURITY ALERT: Found secrets in git-tracked files!"
    check_pass=0
  else
    success "No obvious secrets found in git-tracked files"
  fi

  # Check workspace file exists
  local workspace_file="$PROJECTS_DIR/dev-workspace.code-workspace"
  if [ -f "$workspace_file" ]; then
    success "VS Code workspace file exists: $workspace_file"
  else
    warn "VS Code workspace file not found"
  fi

  mark_done "$step_name"

  if [ $check_pass -eq 1 ]; then
    success "Bootstrap verification complete (all checks passed)"
    return 0
  else
    warn "Bootstrap verification complete (some checks failed)"
    return 0  # Non-blocking
  fi
}

# ── Main Execution Flow ───────────────────────────────────────────────────────

main() {
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        FORCE_BOOTSTRAP=1
        shift
        ;;
      --yes)
        SKIP_PROMPT=1
        shift
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        echo "Use '--help' for usage information"
        exit 1
        ;;
    esac
  done

  # Platform check
  if ! is_wsl2; then
    warn "This script is designed for WSL2 (Ubuntu 24.04+)"
    warn "It may not work correctly on native Linux, macOS, or Windows"
  fi

  info "=== Claude Env Bootstrap ==="
  info "Script directory: $SCRIPT_DIR"
  info "Projects directory: $PROJECTS_DIR"

  if [ "$FORCE_BOOTSTRAP" -eq 1 ]; then
    warn "FORCE mode enabled — re-running all steps"
    rm -f "$BOOTSTRAP_STATE"
  fi

  info ""
  if [ "$SKIP_PROMPT" -eq 0 ] && [ -t 0 ]; then
    info "This script is idempotent. Press Enter to continue, or Ctrl+C to cancel."
    read -r
  elif [ "$SKIP_PROMPT" -eq 0 ]; then
    info "Running in non-interactive mode (stdin not a terminal). Proceeding without prompt."
  else
    info "Proceeding without user prompt (--yes flag enabled)."
  fi

  # Initialize state file if it doesn't exist
  touch "$BOOTSTRAP_STATE"

  # Call step functions in order
  # Each step checks is_done before acting
  clone_repos || exit 1
  install_dependencies || exit 1
  setup_azure_auth || exit 1
  setup_plugins || exit 1
  install_hooks || exit 1
  generate_workspace || exit 1
  verify_bootstrap || exit 1

  info ""
  success "Bootstrap complete!"
  info "All setup steps finished."
  info ""
  info "Next steps:"
  info "  1. Open workspace: code $PROJECTS_DIR/dev-workspace.code-workspace"
  info "  2. Review logs: cat $BOOTSTRAP_STATE.log"
  info "  3. Verify setup: bash infrastructure/wsl/verify-setup.sh"
}

# Run main
main "$@"
