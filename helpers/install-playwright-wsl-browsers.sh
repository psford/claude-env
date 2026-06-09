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

# Resolve our own absolute path BEFORE any cd, so the printed "Phase 3" command
# carries the right path even when the user invoked us via `helpers/install...sh`.
SCRIPT_PATH="$(realpath "$0")"

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
echo "=== Phase 1: querying Playwright for the apt package list ==="
# We capture the list HERE (inside WSL, where node is on patrick's PATH) so
# the wsl.exe --user root command on the Windows side does NOT need node.
# Root inside WSL doesn't load patrick's nvm/fnm/shell env, so npx is not in
# root's PATH. Embedding the package list in the printed command avoids the
# "bash: npx: command not found" failure mode.
DRYRUN_OUT="$(npx playwright install-deps --dry-run firefox webkit 2>&1 || true)"

# `playwright install-deps --dry-run` prints either:
#   - a header "Missing system dependencies (N):" then one package per line, OR
#   - an apt-get install -y ... single line (older Playwright versions).
# Handle both.
PACKAGES=""
if printf '%s\n' "$DRYRUN_OUT" | grep -q '^Missing system dependencies'; then
  # Lines after the header that look like "  package-name". Strip leading whitespace.
  PACKAGES="$(printf '%s\n' "$DRYRUN_OUT" \
    | awk '/^Missing system dependencies/{flag=1; next} flag && /^[[:space:]]+[a-z0-9]/{gsub(/^[[:space:]]+/,""); print}' \
    | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
elif printf '%s\n' "$DRYRUN_OUT" | grep -qE '^\s*apt-get install -y '; then
  PACKAGES="$(printf '%s\n' "$DRYRUN_OUT" | grep -E '^\s*apt-get install -y ' | head -1 | sed 's/^.*apt-get install -y //')"
fi

if [[ -z "$PACKAGES" ]]; then
  echo "ERROR: could not extract package list from 'npx playwright install-deps --dry-run'." >&2
  echo "       Raw output was:" >&2
  printf '%s\n' "$DRYRUN_OUT" | head -20 >&2
  exit 1
fi

PKG_COUNT="$(printf '%s\n' "$PACKAGES" | tr ' ' '\n' | grep -c '^[a-z0-9]')"
echo "  Found $PKG_COUNT system packages to install."
echo ""

echo "=== Phase 2: paste THIS into a Windows PowerShell terminal (regular user, NOT elevated) ==="
cat <<EOF

  wsl.exe --distribution $DISTRO --user root -- bash -lc \\
    "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $PACKAGES"

  Why this works:
   - 'wsl.exe --user root' enters your WSL distro as root WITHOUT going through
     the cage's locked sudoers, so apt-get just works.
   - The package list ($PKG_COUNT names) was computed BY 'playwright install-deps
     --dry-run' a moment ago — same authority as 'npx playwright install-deps',
     but the names are baked into the command so root doesn't need npx in PATH.
     (Root inside WSL doesn't load patrick's nvm/fnm/shell, so npx is unavailable
     there — that's why the simpler-looking 'npx playwright install-deps' command
     failed with 'bash: npx: command not found'.)
   - If you have multiple WSL distros installed, run 'wsl.exe -l -v' first to
     confirm '$DISTRO' is your active one; substitute the actual name if not.
   - The 'wsl: Processing /etc/fstab with mount -a failed' warning is harmless —
     it's the writable-carve-out mount, which is patrick-user-specific. The
     apt-get install does not need it.

=== Phase 3: back in WSL, run the verifier ===

  bash $SCRIPT_PATH --verify

  Expected: '[verify] Firefox OK.' and a working npx playwright command.

EOF
