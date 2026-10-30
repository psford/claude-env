#!/usr/bin/env bash
# install-gitleaks.sh — gitleaks (secret scanner), in user space.
#
# Installs (no sudo; the WSL cage password-gates apt):
#   ~/.local/bin/gitleaks   official GitHub release tarball, sha256-verified against
#                           the checksums file published with the same release
#
# Why: ~/.claude/hooks/session-stop-backup.sh (psford/claude-config) runs
# `gitleaks git --pre-commit --staged` before each ~/.claude auto-commit, and
# commits nothing when gitleaks is missing.
#
# Idempotent: skips the download when ~/.local/bin/gitleaks already reports
# GITLEAKS_VERSION; any other version is replaced.
# Usage: bash install-gitleaks.sh
#
# Source: github.com/gitleaks/gitleaks (MIT). verify-setup.sh reads
# GITLEAKS_VERSION from this file, so a bump here is the whole upgrade.
set -euo pipefail

GITLEAKS_VERSION="8.30.1"

BIN="$HOME/.local/bin"
RELEASES="https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION"

log() { echo "[install-gitleaks] $*"; }

mkdir -p "$BIN"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -x "$BIN/gitleaks" ] && [ "$("$BIN/gitleaks" version 2>/dev/null)" = "$GITLEAKS_VERSION" ]; then
  log "gitleaks $GITLEAKS_VERSION already installed"
else
  tarball="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
  log "Downloading $tarball..."
  curl -sSfL -o "$WORK/$tarball" "$RELEASES/$tarball"
  curl -sSfL -o "$WORK/checksums.txt" "$RELEASES/gitleaks_${GITLEAKS_VERSION}_checksums.txt"
  expected="$(grep " $tarball\$" "$WORK/checksums.txt" | cut -d' ' -f1)"
  echo "$expected  $WORK/$tarball" | sha256sum -c -
  tar -xzf "$WORK/$tarball" -C "$WORK" gitleaks
  install -m 0755 "$WORK/gitleaks" "$BIN/gitleaks"
fi

log "gitleaks $("$BIN/gitleaks" version)"
