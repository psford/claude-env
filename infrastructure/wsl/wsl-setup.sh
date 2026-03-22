#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# WSL2 Claude Code Sandbox — Full Environment Setup
# Run this script inside a fresh Ubuntu WSL2 distro to install all tooling.
# Usage: bash wsl-setup.sh
#
# This script is idempotent — safe to re-run on an existing environment.

LOG_FILE="/tmp/wsl-setup-$(date +%Y%m%d-%H%M%S).log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
trap 'echo "[ERROR] Setup failed at line $LINENO" | tee -a "$LOG_FILE"' ERR

log "=== WSL2 Claude Code Sandbox Setup ==="
log "Log file: $LOG_FILE"

# ── Phase 1: WSL2 isolation (must run first) ────────────────────────────
# Create /etc/wsl.conf with read-only Windows mount.
# automount=true with ro option: VS Code Remote-WSL needs Windows filesystem access,
# but read-only prevents Claude from modifying Windows files.
# appendWindowsPath=false: keeps Windows executables off PATH.
if ! grep -q "automount" /etc/wsl.conf 2>/dev/null; then
  log "Configuring /etc/wsl.conf (read-only automount)..."
  sudo tee /etc/wsl.conf > /dev/null << 'WSLCONF'
[automount]
enabled=true
options=metadata,ro
mountFsTab=false

[interop]
enabled=true
appendWindowsPath=false

[boot]
systemd=true

[user]
default=patrick
WSLCONF
  log "NOTE: wsl.conf created. WSL2 must be restarted (wsl --shutdown) for automount changes to take effect."
  log "If this is a rebuild, restart WSL2 now and re-run this script."
else
  log "/etc/wsl.conf already configured"
fi

# ── Phase 2A: System packages ──────────────────────────────────────────
log "Updating apt packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  build-essential \
  curl \
  wget \
  unzip \
  jq \
  software-properties-common \
  apt-transport-https \
  ca-certificates \
  gnupg \
  lsb-release \
  libicu-dev \
  libssl-dev \
  zlib1g-dev \
  2>&1 | tee -a "$LOG_FILE"

# ── Phase 2B: .NET 8 SDK ───────────────────────────────────────────────
if ! command -v dotnet &>/dev/null || ! dotnet --list-sdks | grep -q "^8\."; then
  log "Installing .NET 8 SDK..."
  # Add Microsoft package feed
  wget -q "https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb" -O /tmp/packages-microsoft-prod.deb
  sudo dpkg -i /tmp/packages-microsoft-prod.deb
  rm /tmp/packages-microsoft-prod.deb
  sudo apt-get update -qq
  sudo apt-get install -y -qq dotnet-sdk-8.0 2>&1 | tee -a "$LOG_FILE"
else
  log ".NET 8 SDK already installed: $(dotnet --version)"
fi

# ── Phase 2C: Python 3 ─────────────────────────────────────────────────
log "Installing Python 3 and venv..."
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")
sudo apt-get install -y -qq python3 python3-pip python3-venv "python${PY_VERSION}-venv" 2>&1 | tee -a "$LOG_FILE"
log "Python 3 installed: $(python3 --version)"

# Install Python packages in a virtual environment (Ubuntu 24.04 enforces PEP 668)
VENV_DIR="$HOME/.venv"
log "Setting up Python virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet \
  requests \
  python-dotenv \
  fastapi \
  uvicorn \
  playwright \
  anthropic \
  slack-bolt \
  slack-sdk \
  2>&1 | tee -a "$LOG_FILE"

# Add venv activation to .bashrc so it's always active
if ! grep -q "source.*\.venv/bin/activate" "$HOME/.bashrc" 2>/dev/null; then
  echo 'source "$HOME/.venv/bin/activate"' >> "$HOME/.bashrc"
fi

# ── Phase 2D: Node.js via nvm ──────────────────────────────────────────
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  log "Installing nvm..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  # Source nvm for current session
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
else
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  log "nvm already installed"
fi

if ! command -v node &>/dev/null || ! node --version | grep -q "^v20\."; then
  log "Installing Node.js 20 LTS..."
  nvm install 20
  nvm alias default 20
  nvm use 20
else
  log "Node.js already installed: $(node --version)"
fi

# ── Phase 2E: Azure CLI ────────────────────────────────────────────────
if ! command -v az &>/dev/null; then
  log "Installing Azure CLI..."
  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash 2>&1 | tee -a "$LOG_FILE"
else
  log "Azure CLI already installed: $(az --version | head -1)"
fi

# ── Phase 2F: Git configuration ────────────────────────────────────────
log "Configuring Git..."
git config --global user.name "Patrick Ford"
# Email must be set manually on first run. Check if already configured.
CURRENT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")
if [ -z "$CURRENT_EMAIL" ]; then
  log "WARNING: Git email not configured. Set it manually after setup:"
  log "  git config --global user.email 'your@email.com'"
else
  log "Git email already configured: $CURRENT_EMAIL"
fi
git config --global init.defaultBranch main
git config --global core.autocrlf input
git config --global pull.rebase false

# Ensure .ssh directory exists before generating keys
mkdir -p "$HOME/.ssh"

# SSH key for GitHub — generate if not present
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
  log "Generating SSH key for GitHub..."
  ssh-keygen -t ed25519 -C "wsl2-claude-sandbox" -f "$HOME/.ssh/id_ed25519" -N ""
  chmod 600 "$HOME/.ssh/id_ed25519"
  log "SSH public key (add to GitHub):"
  cat "$HOME/.ssh/id_ed25519.pub"
  log "Add this key at: https://github.com/settings/keys"
else
  log "SSH key already exists"
fi

# GitHub SSH config
if ! grep -q "github.com" "$HOME/.ssh/config" 2>/dev/null; then
  cat >> "$HOME/.ssh/config" << 'SSHEOF'

Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
SSHEOF
  chmod 600 "$HOME/.ssh/config"
fi

# ── Phase 2G: sqlcmd for connection testing ─────────────────────────────
if [ ! -f /opt/mssql-tools18/bin/sqlcmd ]; then
  log "Installing sqlcmd (mssql-tools18)..."
  # Microsoft prod repo is already configured by the .NET SDK install step above.
  # Just install mssql-tools18 from the existing repo.
  sudo apt-get update -qq
  sudo env ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mssql-tools18 unixodbc-dev 2>&1 | tee -a "$LOG_FILE"
  # Add to PATH
  if ! grep -q "mssql-tools18" "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> "$HOME/.bashrc"
  fi
  export PATH="$PATH:/opt/mssql-tools18/bin"
else
  log "sqlcmd already installed"
fi

# ── Phase 4A: Repository cloning ──────────────────────────────────────────
# Note: repo cloning is handled by bootstrap.sh — wsl-setup.sh focuses on dependencies
REPO_DIR="${CLAUDE_ENV_DIR:-$HOME/projects/claude-env}"
log "Using claude-env at $REPO_DIR"

# ── Phase 4B: Pull secrets from Key Vault ────────────────────────────────
log "Pulling secrets from Azure Key Vault..."
if command -v az &>/dev/null && az account show &>/dev/null; then
  if [ -f "$REPO_DIR/infrastructure/wsl/pull-secrets.sh" ]; then
    bash "$REPO_DIR/infrastructure/wsl/pull-secrets.sh" --output "$REPO_DIR/.env"
  else
    log "WARNING: pull-secrets.sh not found at $REPO_DIR/infrastructure/wsl/"
  fi
else
  log "WARNING: Azure CLI not authenticated. Run 'az login' then re-run pull-secrets.sh"
fi

# ── Phase 4C: Build verification ────────────────────────────────────────
# Note: claude-env contains no app code — build steps handled in each app's bootstrap
log "Skipping app builds (handled by individual app projects)"

# ── Phase 5A: Claude Code CLI ───────────────────────────────────────────
if ! command -v claude &>/dev/null; then
  log "Installing Claude Code..."
  curl -fsSL https://claude.ai/install.sh | bash
else
  log "Claude Code already installed: $(claude --version 2>/dev/null || echo 'installed')"
fi

# ── Phase 5B: Restore Claude config from private repo ───────────────────
CLAUDE_DIR="$HOME/.claude"
if [ ! -d "$CLAUDE_DIR/.git" ]; then
  log "Cloning claude-config..."
  if [ -d "$CLAUDE_DIR" ]; then
    mv "$CLAUDE_DIR" "${CLAUDE_DIR}.bak.$(date +%s)"
  fi
  git clone https://github.com/psford/claude-config.git "$CLAUDE_DIR"
else
  log "Claude config already present, pulling latest..."
  (cd "$CLAUDE_DIR" && git pull --quiet)
fi

# ── Phase 5C: Register plugins natively in WSL2 ─────────────────────────
# Plugin source (marketplace dirs) are synced via git. Registry files
# (installed_plugins.json, known_marketplaces.json) are NOT synced because
# they contain OS-absolute paths. Each OS generates its own registry.

log "Phase 5C: Registering Claude Code plugins..."

if ! command -v claude &>/dev/null; then
    log "WARNING: 'claude' not on PATH — skipping plugin registration"
    log "         Run manually after installing Claude Code:"
    log "           claude plugin marketplace add ~/.claude/plugins/marketplaces/ed3d-plugins"
    log "           claude plugin marketplace add ~/.claude/plugins/marketplaces/patricks-local"
else
    # Register marketplaces
    for marketplace_dir in "${CLAUDE_DIR}/plugins/marketplaces"/*/; do
        marketplace_name=$(basename "$marketplace_dir")
        if [ -f "${CLAUDE_DIR}/plugins/known_marketplaces.json" ] && \
           grep -q "$marketplace_name" "${CLAUDE_DIR}/plugins/known_marketplaces.json" 2>/dev/null; then
            log "  Marketplace '$marketplace_name' already registered"
        elif [ -d "$marketplace_dir" ]; then
            log "  Adding marketplace: $marketplace_name"
            claude plugin marketplace add "$marketplace_dir" 2>/dev/null || \
                log "  WARNING: Failed to add marketplace $marketplace_name"
        fi
    done

    # Install plugins from each marketplace
    if [ -f "${CLAUDE_DIR}/plugins/known_marketplaces.json" ]; then
        for marketplace_dir in "${CLAUDE_DIR}/plugins/marketplaces"/*/; do
            marketplace_name=$(basename "$marketplace_dir")
            # Find plugin subdirs in the marketplace
            for plugin_dir in "${marketplace_dir}plugins"/*/; do
                [ -d "$plugin_dir" ] || continue
                plugin_name=$(basename "$plugin_dir")
                full_name="${plugin_name}@${marketplace_name}"
                if [ -f "${CLAUDE_DIR}/plugins/installed_plugins.json" ] && \
                   grep -q "$plugin_name" "${CLAUDE_DIR}/plugins/installed_plugins.json" 2>/dev/null; then
                    log "  Plugin '$full_name' already installed"
                else
                    log "  Installing plugin: $full_name"
                    claude plugin install "$full_name" 2>/dev/null || \
                        log "  WARNING: Failed to install $full_name"
                fi
            done
        done
    fi

    log "Installed plugins:"
    claude plugin list 2>/dev/null || log "(claude plugin list not available)"
fi

# ── Phase 5D: Install git hooks in ~/.claude repo ───────────────────────
log "Phase 5D: Installing git hooks in ~/.claude repo..."
HOOKS_INSTALLER="${REPO_DIR}/infrastructure/wsl/install-claude-config-hooks.sh"
if [ -f "$HOOKS_INSTALLER" ]; then
    bash "$HOOKS_INSTALLER"
    log "Git hooks installed in ${CLAUDE_DIR}/.git/hooks/"
else
    log "WARNING: install-claude-config-hooks.sh not found at ${HOOKS_INSTALLER}"
fi

# ── Summary ─────────────────────────────────────────────────────────────
log ""
log "=== Setup Complete ==="
log "  .NET:    $(dotnet --version 2>/dev/null || echo 'FAILED')"
log "  Python:  $(python3 --version 2>/dev/null || echo 'FAILED')"
log "  Node:    $(node --version 2>/dev/null || echo 'FAILED')"
log "  npm:     $(npm --version 2>/dev/null || echo 'FAILED')"
log "  az:      $(az --version 2>/dev/null | head -1 || echo 'FAILED')"
log "  git:     $(git --version 2>/dev/null || echo 'FAILED')"
log "  sqlcmd:  $(sqlcmd --version 2>/dev/null | head -1 || echo 'FAILED')"
log "  Claude:  $(claude --version 2>/dev/null || echo 'FAILED')"
log "  Config:  $([ -d "$HOME/.claude/.git" ] && echo 'git-backed' || echo 'NOT git-backed')"
log "  Repo:    $REPO_DIR ($(cd "$REPO_DIR" && git branch --show-current))"
log "  .env:    $([ -f "$REPO_DIR/.env" ] && echo 'present' || echo 'MISSING')"
log ""
log "Next steps:"
log "  1. Add SSH key to GitHub (if newly generated)"
log "  2. Run: az login"
log "  3. Continue to Phase 3 (SQL connectivity)"
log ""
log "Full log: $LOG_FILE"
