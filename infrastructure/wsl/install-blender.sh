#!/usr/bin/env bash
# install-blender.sh — Blender LTS + the Blender Lab MCP server, in user space,
# running on the Windows GPU through WSLg.
#
# Installs (no sudo; the WSL cage password-gates apt):
#   ~/.local/opt/blender-<ver>-linux-x64   official tarball, sha256-verified
#   ~/.local/bin/blender                   launcher that puts Blender on the GPU (below)
#   Blender Lab MCP add-on ("mcp")         release zip, pinned sha256, enabled
#   ~/.local/opt/blender-mcp-<ver>/venv    blender-mcp relay (stdio MCP server)
#   ~/.local/bin/blender-mcp               -> the relay, registered with Claude Code at user scope
# and sets the two Blender preferences the setup needs:
#   online access ON    the add-on won't open its localhost socket without it
#   GPU backend OPENGL  Mesa's d3d12 OpenGL driver reaches the GPU; there is no dzn Vulkan driver
#
# The GPU path (see infrastructure/wsl/CLAUDE.md): Mesa's OpenGL-on-DirectX-12 driver
# (GALLIUM_DRIVER=d3d12), pinned to the NVIDIA adapter, with Blender on X11. Blender's
# Wayland window on d3d12 breaks the WSLg compositor connection; an unreachable
# WAYLAND_DISPLAY makes Blender fall back to X11. The launcher sets all three.
#
# Idempotent: re-running skips what is already in place and rewrites the launcher and prefs.
# Usage: bash install-blender.sh
#
# BLENDER_VERSION tracks Patrick's Windows Blender (same minor) so .blend files
# open on both. Bumping MCP_VERSION means re-pinning MCP_ZIP_SHA256.
set -euo pipefail

BLENDER_VERSION="5.2.3"
BLENDER_MINOR="${BLENDER_VERSION%.*}"
MCP_VERSION="1.0.3"
# sha256 of mcp-1.0.3.zip; its files match the v1.0.3 tag byte for byte.
MCP_ZIP_SHA256="a7a9da816192502e5a0a202a396444e266b47d8fc4f74ad4698048bd43040707"

OPT="$HOME/.local/opt"
BIN="$HOME/.local/bin"
BLENDER_DIR="$OPT/blender-$BLENDER_VERSION-linux-x64"
MCP_DIR="$OPT/blender-mcp-$MCP_VERSION"
ADDON_MANIFEST="$HOME/.config/blender/$BLENDER_MINOR/extensions/user_default/mcp/blender_manifest.toml"
RELEASES="https://download.blender.org/release/Blender$BLENDER_MINOR"
MCP_REPO="https://projects.blender.org/lab/blender_mcp"

log() { echo "[install-blender] $*"; }

mkdir -p "$OPT" "$BIN"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ── Blender ──────────────────────────────────────────────────────────────
if [ -x "$BLENDER_DIR/blender" ]; then
  log "Blender $BLENDER_VERSION already installed"
else
  tarball="blender-$BLENDER_VERSION-linux-x64.tar.xz"
  log "Downloading $tarball..."
  curl -sSfL -o "$WORK/$tarball" "$RELEASES/$tarball"
  curl -sSfL -o "$WORK/blender.sha256" "$RELEASES/blender-$BLENDER_VERSION.sha256"
  expected="$(grep " $tarball\$" "$WORK/blender.sha256" | cut -d' ' -f1)"
  echo "$expected  $WORK/$tarball" | sha256sum -c -
  tar -xJf "$WORK/$tarball" -C "$OPT"
fi
ln -sfn "$BLENDER_DIR" "$OPT/blender-$BLENDER_MINOR"

# ── GPU launcher (always rewritten) ──────────────────────────────────────
# Every caller goes through it: Patrick's launches, Claude's, and the MCP server's
# *_for_cli tools (which run `blender` from PATH).
rm -f "$BIN/blender"
cat > "$BIN/blender" <<EOF
#!/bin/sh
# Blender on the NVIDIA GPU under WSLg. Written by claude-env/infrastructure/wsl/install-blender.sh.
# X11 (XWayland), not Wayland: Blender's Wayland window on Mesa d3d12 breaks the WSLg
# compositor connection. An unreachable WAYLAND_DISPLAY makes Blender fall back to X11.
# d3d12: Mesa's OpenGL-on-DirectX-12 driver, pinned to the NVIDIA adapter (adapter 0 is
# the CPU's integrated Radeon).
export WAYLAND_DISPLAY=blender-uses-x11
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME="\${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"
exec "\$HOME/.local/opt/blender-$BLENDER_MINOR/blender" "\$@"
EOF
chmod +x "$BIN/blender"

# ── Blender Lab MCP add-on ───────────────────────────────────────────────
if grep -qs "^version = \"$MCP_VERSION\"" "$ADDON_MANIFEST"; then
  log "MCP add-on $MCP_VERSION already installed"
else
  zip="mcp-$MCP_VERSION.zip"
  log "Downloading $zip..."
  curl -sSfL -o "$WORK/$zip" "$MCP_REPO/releases/download/v$MCP_VERSION/$zip"
  echo "$MCP_ZIP_SHA256  $WORK/$zip" | sha256sum -c -
  "$BIN/blender" --factory-startup -c extension install-file -r user_default -e "$WORK/$zip"
fi

# ── Preferences (always re-applied) ──────────────────────────────────────
"$BIN/blender" -b --python-expr '
import addon_utils, bpy
addon_utils.enable("bl_ext.user_default.mcp", default_set=True, persistent=True)
s = bpy.context.preferences.system
s.use_online_access = True
s.gpu_backend = "OPENGL"
bpy.ops.wm.save_userpref()
print("INSTALL_BLENDER_PREFS online_access=%s gpu_backend=%s" % (s.use_online_access, s.gpu_backend))
' 2>&1 | grep INSTALL_BLENDER_PREFS

# ── blender-mcp relay ────────────────────────────────────────────────────
if [ -x "$MCP_DIR/venv/bin/blender-mcp" ]; then
  log "blender-mcp $MCP_VERSION already installed"
else
  log "Installing blender-mcp $MCP_VERSION..."
  python3 -m venv "$MCP_DIR/venv"
  "$MCP_DIR/venv/bin/pip" install -q --upgrade pip
  "$MCP_DIR/venv/bin/pip" install -q "git+$MCP_REPO.git@v$MCP_VERSION#subdirectory=mcp"
fi
ln -sfn "$MCP_DIR" "$OPT/blender-mcp"
ln -sfn "$OPT/blender-mcp/venv/bin/blender-mcp" "$BIN/blender-mcp"

# ── Register with Claude Code (user scope) ───────────────────────────────
# User scope, not a repo's .mcp.json: desktop sessions start in $HOME, so a
# project file in the design repo is never read. Takes effect at session start.
if command -v claude >/dev/null 2>&1; then
  if claude mcp get blender >/dev/null 2>&1; then
    log "Claude Code MCP server 'blender' already registered"
  else
    claude mcp add --scope user blender -- blender-mcp
  fi
else
  log "claude CLI not found; register later: claude mcp add --scope user blender -- blender-mcp"
fi

log "$("$BIN/blender" --version | head -1)"
log "GPU: $("$BIN/blender" -b --python-expr 'import gpu; gpu.init(); print("GPU_RENDERER", gpu.platform.renderer_get())' 2>&1 | sed -n 's/^GPU_RENDERER //p')"
log "blender-mcp $("$MCP_DIR/venv/bin/pip" show blender-mcp | sed -n 's/^Version: //p')"
