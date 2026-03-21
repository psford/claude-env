#!/bin/bash
set -e
set -u
set -o pipefail

# WSL2 Claude Code Sandbox — Full Environment Setup
# Run this script inside a fresh Ubuntu WSL2 distro to install all tooling.
# Usage: bash wsl-setup.sh
#
# This script is idempotent — safe to re-run on an existing environment.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/wsl-setup-$(date +%Y%m%d-%H%M%S).log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
err() { log "ERROR: $*" >&2; }

log "=== WSL2 Claude Code Sandbox Setup ==="
log "Log file: $LOG_FILE"

# ── Phase 1: WSL2 isolation (must run first) ────────────────────────────
# Create /etc/wsl.conf to disable automount if not already configured.
# This ensures Windows drives are never mounted, even on a fresh rebuild.
if ! grep -q "automount" /etc/wsl.conf 2>/dev/null; then
  log "Configuring /etc/wsl.conf (disable automount)..."
  sudo tee /etc/wsl.conf > /dev/null << 'WSLCONF'
[automount]
enabled=false
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
  wget -q https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/packages-microsoft-prod.deb -O /tmp/packages-microsoft-prod.deb
  sudo dpkg -i /tmp/packages-microsoft-prod.deb
  rm /tmp/packages-microsoft-prod.deb
  sudo apt-get update -qq
  sudo apt-get install -y -qq dotnet-sdk-8.0 2>&1 | tee -a "$LOG_FILE"
else
  log ".NET 8 SDK already installed: $(dotnet --version)"
fi

# ── Phase 2C: Python 3 ─────────────────────────────────────────────────
log "Installing Python 3 and venv..."
sudo apt-get install -y -qq python3 python3-pip python3-venv python3.12-venv 2>&1 | tee -a "$LOG_FILE"
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

# SSH key for GitHub — generate if not present
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
  log "Generating SSH key for GitHub..."
  ssh-keygen -t ed25519 -C "wsl2-claude-sandbox" -f "$HOME/.ssh/id_ed25519" -N ""
  log "SSH public key (add to GitHub):"
  cat "$HOME/.ssh/id_ed25519.pub"
  log "Add this key at: https://github.com/settings/keys"
else
  log "SSH key already exists"
fi

# GitHub SSH config
mkdir -p "$HOME/.ssh"
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
log ""
log "Next steps:"
log "  1. Add SSH key to GitHub (if newly generated)"
log "  2. Run: az login"
log "  3. Continue to Phase 3 (SQL connectivity)"
log ""
log "Full log: $LOG_FILE"
