#!/usr/bin/env bash
# install-playwright-wsl-browsers.sh
#
# Install Playwright Firefox + Webkit browsers on a WSL2 distro where the
# `sudoers` file is locked (the claude-env cage). The browser binaries
# themselves don't need root, but the system shared libraries Firefox/Webkit
# link against (libnspr4, libnss3, libdbus-glib-1-2, libenchant-2-2,
# libwoff1, libGLESv2, etc.) MUST be installed via apt-get as root.
#
# The locked-sudoers carve-out is: run `wsl.exe --user root` from a Windows
# host terminal. That bypasses the cage's sudoers lock for one-shot apt
# operations without unlocking the cage.
#
# Run-flow:
#   1. From inside WSL (this script): downloads browser binaries, computes
#      missing system libs, and PRINTS the exact Windows PowerShell command
#      to run to install those libs as root.
#   2. From Windows PowerShell (operator step): paste the printed
#      `wsl.exe --user root -- bash -c "apt-get install -y ..."` line.
#   3. From inside WSL again (this script with `--verify`): re-runs
#      `playwright install` (idempotent — binaries already present) and
#      verifies a Firefox process can launch.
#
# Usage:
#   bash helpers/install-playwright-wsl-browsers.sh           # phase 1
#   bash helpers/install-playwright-wsl-browsers.sh --verify  # post-phase-2
#
# Optional env:
#   PROJECT_DIR=/path/to/project   defaults to /home/patrick/projects/photo-portfolio
#                                  (any project with @playwright/test in node_modules works)
#
# Exit codes:
#   0  success (or phase 1 completed and printed instructions)
#   1  binary download failed, or verify failed
#   2  not running inside WSL2

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/patrick/projects/photo-portfolio}"
VERIFY_ONLY=0
if [[ "${1:-}" == "--verify" ]]; then
  VERIFY_ONLY=1
fi

# --- Sanity: we must be inside WSL ---
if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "ERROR: This script is for WSL2 only. /proc/version does not look like WSL." >&2
  exit 2
fi

DISTRO="${WSL_DISTRO_NAME:-Ubuntu}"

cd "$PROJECT_DIR"

if [[ ! -d node_modules/@playwright ]]; then
  echo "ERROR: $PROJECT_DIR has no @playwright in node_modules." >&2
  echo "       Install playwright first or set PROJECT_DIR to a playwright-using project." >&2
  exit 1
fi

# --- Verify phase (post-operator-step) ---
if [[ "$VERIFY_ONLY" -eq 1 ]]; then
  echo "[verify] Re-running playwright install (idempotent)..."
  npx playwright install firefox webkit

  echo ""
  echo "[verify] Launching Firefox in headless mode to confirm system libs resolve..."
  set +e
  npx playwright test --project=firefox --list >/dev/null 2>&1
  FIREFOX_RC=$?
  set -e
  if [[ "$FIREFOX_RC" -ne 0 ]]; then
    echo "ERROR: Firefox still cannot launch. Re-run Phase 2 (Windows step)." >&2
    npx playwright test --project=firefox --list 2>&1 | tail -20 >&2 || true
    exit 1
  fi

  echo "[verify] Firefox OK."
  echo ""
  echo "[verify] Probing Webkit..."
  set +e
  npx playwright test --project=webkit --list >/dev/null 2>&1
  WEBKIT_RC=$?
  set -e
  if [[ "$WEBKIT_RC" -ne 0 ]]; then
    echo "WARN: Webkit project not listable. Webkit on WSL2 sometimes needs extra"
    echo "      libraries (libwebpdemux, libavif, libharfbuzz-icu0). If Webkit"
    echo "      coverage matters, re-run Phase 2 with the extended dep list."
  else
    echo "[verify] Webkit OK."
  fi

  echo ""
  echo "[verify] Done. Run e2e on Firefox with:"
  echo "  cd $PROJECT_DIR && npx playwright test --project=firefox"
  exit 0
fi

# --- Phase 1: download binaries ---
echo "=== Phase 1: downloading Playwright Firefox + Webkit binaries ==="
echo "  PROJECT_DIR=$PROJECT_DIR"
echo "  WSL distro=$DISTRO"
echo ""

# Binaries go to ~/.cache/ms-playwright/ which is shared across projects.
npx playwright install firefox webkit

echo ""
echo "=== Phase 2: run THIS in a Windows PowerShell terminal (regular user, NOT elevated) ==="
cat <<EOF

  wsl.exe --distribution $DISTRO --user root -- bash -lc \\
    "cd $PROJECT_DIR && npx playwright install-deps firefox webkit"

  Why this works:
   - 'wsl.exe --user root' enters your WSL distro as root WITHOUT going through
     the cage's locked sudoers, so apt-get just works.
   - We delegate to 'npx playwright install-deps' (rather than handcrafting an
     apt-get list) so Playwright itself decides which packages to install for
     the exact browser versions in $PROJECT_DIR/node_modules. That stays correct
     across Playwright upgrades.
   - If you have multiple WSL distros installed, run 'wsl.exe -l -v' first to
     confirm '$DISTRO' is your active one; substitute the actual name if not.

=== Phase 3: back in WSL, run the verifier ===

  bash $(realpath "$0") --verify

  Expected: '[verify] Firefox OK.' and a working npx playwright command.

EOF
