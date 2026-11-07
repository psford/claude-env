#!/usr/bin/env bash
# install-freecad.sh — FreeCAD and the Robust MCP bridge, in user space, running on
# the Windows GPU through WSLg.
#
# Installs (no sudo; the WSL cage password-gates apt):
#   ~/.local/opt/freecad-<ver>/squashfs-root      official AppImage, pinned sha256, unpacked
#                                                 (WSL has no FUSE to mount it)
#   ~/.local/bin/freecad                          launcher that puts FreeCAD on the GPU
#   ~/.local/opt/freecad-robust-mcp-<ver>/venv    MCP server, from a reviewed commit
#   ~/.local/share/FreeCAD/v<minor>/Mod/RobustMCPBridge   workbench, from a reviewed commit
# and sets up the bridge:
#   socket port 9877    Blender's MCP add-on holds 9876; XML-RPC stays on 9875
#   pairing             ~/.freecad-robust-mcp/, private, created once
#   registered          with Claude Code at user scope as "freecad", in XML-RPC mode
#
# The bridge's auto-start stays off, so it listens only once it's started in FreeCAD.
# FREECAD_ALLOW_UNSAFE_CODE stays off, so execute_python and the macro tools aren't offered.
# Why this bridge and what was reviewed: docs/decisions.md, 2026-11-07.
#
# Idempotent: re-running skips what is already in place and rewrites the launcher. It
# leaves FreeCAD's preferences alone while FreeCAD is running, because FreeCAD writes
# them back when it closes.
# Usage: bash install-freecad.sh
#
# Bumping the bridge means reviewing the new code first, then re-pinning its commits.
set -euo pipefail

FREECAD_VERSION="1.1.4"
FREECAD_PROFILE="v1-1"
APPIMAGE="FreeCAD_$FREECAD_VERSION-Linux-x86_64-py311.AppImage"
APPIMAGE_SHA256="f6dc6ba676e5ac96a565ebc8d657232f94c6158e85b4352141bd1a46f6b43434"
BRIDGE_VERSION="0.7.0"
BRIDGE_SERVER_COMMIT="b6a510a8004b68d42d675fae3593978067c24282"     # robust-mcp-server-v0.7.0
BRIDGE_WORKBENCH_COMMIT="753b16886bdbb15fcedac78a46d33e1278a91651"  # robust-mcp-workbench-v0.7.1
BRIDGE_SOCKET_PORT=9877
BRIDGE_XMLRPC_PORT=9875

OPT="$HOME/.local/opt"
BIN="$HOME/.local/bin"
FREECAD_DIR="$OPT/freecad-$FREECAD_VERSION"
BRIDGE_DIR="$OPT/freecad-robust-mcp-$BRIDGE_VERSION"
MOD_DIR="$HOME/.local/share/FreeCAD/$FREECAD_PROFILE/Mod"
CREDENTIAL="$HOME/.freecad-robust-mcp/bridge-credential.json"
RELEASES="https://github.com/FreeCAD/FreeCAD/releases/download/$FREECAD_VERSION"
BRIDGE_REPO="https://github.com/spkane/freecad-addon-robust-mcp-server.git"

log() { echo "[install-freecad] $*"; }

mkdir -p "$OPT" "$BIN" "$MOD_DIR"
WORK="$(mktemp -d "$OPT/.install-freecad.XXXXXX")"     # beside the install: it unpacks to 3 GB
trap 'rm -rf "$WORK"' EXIT

# ── FreeCAD ────────────────────────────────────────────────────────────
if [ -x "$FREECAD_DIR/squashfs-root/AppRun" ]; then
  log "FreeCAD $FREECAD_VERSION already installed"
else
  log "Downloading $APPIMAGE..."
  curl -sSfL -o "$WORK/$APPIMAGE" "$RELEASES/$APPIMAGE"
  echo "$APPIMAGE_SHA256  $WORK/$APPIMAGE" | sha256sum -c -
  chmod +x "$WORK/$APPIMAGE"
  (cd "$WORK" && "./$APPIMAGE" --appimage-extract >/dev/null)
  mkdir -p "$FREECAD_DIR"
  mv "$WORK/squashfs-root" "$FREECAD_DIR/"
fi
ln -sfn "$FREECAD_DIR" "$OPT/freecad"

# ── GPU launcher (always rewritten) ────────────────────────────────────
rm -f "$BIN/freecad"
cat > "$BIN/freecad" <<'EOF'
#!/bin/sh
# FreeCAD on the NVIDIA GPU under WSLg. Written by claude-env/infrastructure/wsl/install-freecad.sh.
# AppRun puts Qt on X11 (XWayland). d3d12: Mesa's OpenGL-on-DirectX-12 driver, pinned to
# the NVIDIA adapter (adapter 0 is the CPU's integrated Radeon).
# `freecad freecadcmd <script>` runs FreeCAD's console binary instead of the GUI.
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME="${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"
exec "$HOME/.local/opt/freecad/squashfs-root/AppRun" "$@"
EOF
chmod +x "$BIN/freecad"

# ── Bridge: server and workbench, from the reviewed commits ────────────
if [ -x "$BRIDGE_DIR/venv/bin/freecad-mcp" ] && [ -d "$MOD_DIR/RobustMCPBridge" ]; then
  log "Robust MCP bridge $BRIDGE_VERSION already installed"
else
  log "Installing the Robust MCP bridge from its reviewed commits..."
  git clone -q "$BRIDGE_REPO" "$WORK/bridge"
  git -C "$WORK/bridge" -c advice.detachedHead=false checkout -q "$BRIDGE_SERVER_COMMIT"
  python3 -m venv "$BRIDGE_DIR/venv"
  "$BRIDGE_DIR/venv/bin/pip" install -q --upgrade pip
  "$BRIDGE_DIR/venv/bin/pip" install -q "$WORK/bridge"
  git -C "$WORK/bridge" -c advice.detachedHead=false checkout -q "$BRIDGE_WORKBENCH_COMMIT"
  "$BRIDGE_DIR/venv/bin/python" "$WORK/bridge/scripts/install_workbench.py" --mod-dir "$MOD_DIR"
fi

# ── Bridge preferences ─────────────────────────────────────────────────
if pgrep -x freecad >/dev/null 2>&1; then
  log "FreeCAD is running: leaving its preferences alone. Re-run after closing it to set the socket port."
else
  cat > "$WORK/prefs.py" <<EOF
import FreeCAD
p = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/RobustMCPBridge")
p.SetInt("SocketPort", $BRIDGE_SOCKET_PORT)
p.SetInt("XMLRPCPort", $BRIDGE_XMLRPC_PORT)
FreeCAD.saveParameter()
print("INSTALL_FREECAD_PREFS socket=%d xmlrpc=%d autostart=%s" % (p.GetInt("SocketPort"), p.GetInt("XMLRPCPort"), p.GetBool("AutoStart", False)))
EOF
  "$BIN/freecad" freecadcmd "$WORK/prefs.py" </dev/null 2>&1 | grep INSTALL_FREECAD_PREFS
fi

# ── Pairing (once: the command refuses to replace one) ─────────────────
if [ -f "$CREDENTIAL" ]; then
  log "Bridge pairing already present"
else
  "$BRIDGE_DIR/venv/bin/freecad-mcp" --pair-bridge | sed -E 's/client [0-9a-f]+/client <id>/'
fi

# ── Register with Claude Code (user scope) ─────────────────────────────
# User scope, as for Blender: desktop sessions start in $HOME. The server connects as it
# starts and exits if nothing answers, so the bridge has to be running before a session starts.
if command -v claude >/dev/null 2>&1; then
  if grep -qs '"freecad-mcp"\|freecad-robust-mcp' "$HOME/.claude.json"; then
    log "Claude Code MCP server 'freecad' already registered"
  else
    claude mcp add --scope user freecad -e FREECAD_MODE=xmlrpc -e "FREECAD_XMLRPC_PORT=$BRIDGE_XMLRPC_PORT" \
      -e "FREECAD_SOCKET_PORT=$BRIDGE_SOCKET_PORT" -- "$BRIDGE_DIR/venv/bin/freecad-mcp"
  fi
else
  log "claude CLI not found; register later (see infrastructure/wsl/CLAUDE.md)"
fi

log "FreeCAD: $("$FREECAD_DIR/squashfs-root/usr/bin/freecadcmd" --version </dev/null 2>/dev/null | head -1)"
log "Bridge: $("$BRIDGE_DIR/venv/bin/freecad-mcp" --version 2>/dev/null | head -1)"
