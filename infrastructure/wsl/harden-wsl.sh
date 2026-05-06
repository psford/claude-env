#!/usr/bin/env bash
# harden-wsl.sh
#
# Locks down the WSL sandbox so Claude Code (running as user 'patrick') cannot:
#   - Execute Windows binaries via WSL interop
#   - Mount additional Windows paths (sudo mount blocked without password)
#   - Edit /etc/wsl.conf, /etc/sudoers, /etc/fstab (immutable)
#   - Sudo arbitrary commands without password
#
# THREAT MODEL: Claude itself. The cage assumes Claude can write any file
# Claude has access to, run any binary on PATH, and call sudo for anything
# in its sudoers grant. Defense is at the OS level (WSL kernel + sudoers +
# ext4 immutable bit), not at the prompt or markdown layer.
#
# YOU run this script, not Claude. Once installed, the cage requires your
# sudo password to undo. If Claude could install it, Claude could uninstall
# it -- so installation is on the honor system the first time, enforcement-
# bound thereafter.
#
# Idempotent: safe to re-run. Subsequent runs prompt for your password
# (because the cage itself locks sudo down).
#
# Usage:
#   bash harden-wsl.sh
#
# After running, from Windows PowerShell:
#   wsl --shutdown
# Then reopen WSL and run:
#   bash verify-cage.sh
# All bypass attempts must fail.

set -euo pipefail

CAGE_FILE=/etc/sudoers.d/zz-claude-cage
LEGACY_CAGE_FILE=/etc/sudoers.d/99-claude-cage
DEFAULT_USER_SUDOERS=/etc/sudoers.d/patrick
BACKUP_DIR=/etc/.claude-cage-backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

log() { echo "[harden-wsl] $*"; }
die() { echo "[harden-wsl] ERROR: $*" >&2; exit 1; }

# ── Pre-flight ─────────────────────────────────────────────────
[[ "$(id -un)" == "patrick" ]] || die "run as user 'patrick', not $(id -un)"

cat <<'WARN'

This script installs an OS-level cage for the WSL sandbox.
After it runs, undoing the cage (re-enabling interop, removing chattr +i,
modifying /etc/sudoers, etc.) requires YOUR sudo password.

If your linux user 'patrick' has no password set yet, set one first:
  exit this script, then from Windows PowerShell:
    wsl -d Ubuntu-24.04 -u root passwd patrick
  then come back and re-run harden-wsl.sh.

WARN
read -rp "Type YES to proceed: " CONFIRM
[[ "$CONFIRM" == "YES" ]] || die "aborted"

# Verify sudo works at all (passes through NOPASSWD if active, prompts otherwise)
log "Verifying sudo access..."
sudo true || die "sudo failed"

# ── Backup ─────────────────────────────────────────────────────
log "Backing up current state to $BACKUP_DIR (timestamp $TIMESTAMP)..."
sudo mkdir -p "$BACKUP_DIR"
for f in /etc/wsl.conf /etc/sudoers /etc/fstab; do
    [[ -f "$f" ]] && sudo cp -p "$f" "$BACKUP_DIR/$(basename "$f").$TIMESTAMP"
done
[[ -d /etc/sudoers.d ]] && sudo cp -rp /etc/sudoers.d "$BACKUP_DIR/sudoers.d.$TIMESTAMP"

# ── Remove immutable flags (idempotent re-run) ────────────────
log "Removing immutable flags (no-op on first run)..."
sudo chattr -i /etc/wsl.conf 2>/dev/null || true
sudo chattr -i /etc/fstab 2>/dev/null || true
sudo chattr -i /etc/sudoers 2>/dev/null || true

# ── Layer A: disable WSL → Windows interop ────────────────────
log "Setting [interop] enabled=false in /etc/wsl.conf..."
sudo python3 - <<'PYEOF'
import re, pathlib
p = pathlib.Path('/etc/wsl.conf')
text = p.read_text() if p.exists() else ''

if '[interop]' in text:
    # Walk sections and rewrite the [interop] one
    sections = re.split(r'(?m)^(\[\w+\])\s*$', text)
    out = []
    cur_section = None
    i = 0
    while i < len(sections):
        chunk = sections[i]
        if i % 2 == 1:  # section header
            cur_section = chunk
            out.append(chunk + '\n')
        else:
            if cur_section == '[interop]':
                # Replace or insert enabled=false
                if re.search(r'^enabled\s*=', chunk, re.M):
                    chunk = re.sub(r'^enabled\s*=.*$', 'enabled=false', chunk, flags=re.M)
                else:
                    chunk = '\nenabled=false' + chunk
                # Same for appendWindowsPath (belt-and-suspenders)
                if re.search(r'^appendWindowsPath\s*=', chunk, re.M):
                    chunk = re.sub(r'^appendWindowsPath\s*=.*$', 'appendWindowsPath=false', chunk, flags=re.M)
                else:
                    chunk = '\nappendWindowsPath=false' + chunk
            out.append(chunk)
        i += 1
    text = ''.join(out)
else:
    text = (text.rstrip() + '\n\n[interop]\nenabled=false\nappendWindowsPath=false\n').lstrip()

p.write_text(text)
PYEOF

log "  /etc/wsl.conf [interop] section now:"
sudo awk '/^\[interop\]/{p=1;print;next} /^\[/{p=0} p' /etc/wsl.conf | sed 's/^/    /'

# ── Layer B: install sudo cage ────────────────────────────────
log "Installing $CAGE_FILE..."
sudo tee "$CAGE_FILE" > /dev/null <<'SUDOEOF'
# Claude Cage: restrict sudo for user 'patrick'.
# Threat model: Claude itself.
#
# Filename is 'zz-claude-cage' so it sorts AFTER any existing /etc/sudoers.d
# entry by username (e.g. 'patrick'). Sudoers reads files in lexical order
# and last match wins; ASCII puts digits BEFORE lowercase letters so a
# '99-' prefix is NOT last when other files use letter prefixes.
#
# To extend the NOPASSWD allowlist:
#   sudo visudo -f /etc/sudoers.d/zz-claude-cage

# Tighter security defaults
Defaults:patrick    timestamp_timeout=5
Defaults:patrick    !pwfeedback
Defaults:patrick    use_pty
Defaults:patrick    log_input,log_output

# Default: every sudo by patrick requires patrick's password.
patrick ALL=(ALL:ALL) ALL

# Read-only diagnostic NOPASSWD allowlist.
# Keep this list small. Add only commands that:
#   - read state without modifying it
#   - cannot be redirected to write elsewhere
#   - don't accept arbitrary shell args that could escalate
Cmnd_Alias CAGE_READ_ONLY = \
    /usr/bin/journalctl, \
    /bin/journalctl, \
    /usr/bin/dmesg, \
    /bin/dmesg, \
    /bin/systemctl status *, \
    /bin/systemctl is-active *, \
    /bin/systemctl is-enabled *, \
    /usr/bin/systemctl status *, \
    /usr/bin/systemctl is-active *, \
    /usr/bin/systemctl is-enabled *

patrick ALL=(ALL) NOPASSWD: CAGE_READ_ONLY
SUDOEOF

sudo chmod 0440 "$CAGE_FILE"

log "Validating sudoers syntax..."
sudo visudo -cf "$CAGE_FILE" || die "sudoers syntax invalid in $CAGE_FILE"
sudo visudo -c || die "overall sudoers validation failed (cage NOT activated; backup at $BACKUP_DIR)"

# Remove the legacy 99-prefixed cage file if a previous run installed it.
if [[ -f "$LEGACY_CAGE_FILE" ]]; then
    log "Removing legacy cage file $LEGACY_CAGE_FILE (replaced by $CAGE_FILE)..."
    sudo rm -f "$LEGACY_CAGE_FILE"
fi

# Remove the WSL-default per-user NOPASSWD: ALL grant. The cage now provides
# patrick's sudo rules; leaving this file present is misleading and (if the
# cage filename ever sorts before it again) dangerous.
# Done LAST among sudoers edits — once removed, sudo requires password
# immediately for everything outside the cage's NOPASSWD allowlist.
if [[ -f "$DEFAULT_USER_SUDOERS" ]]; then
    log "Removing $DEFAULT_USER_SUDOERS (cage now governs patrick's sudo)..."
    sudo cp -p "$DEFAULT_USER_SUDOERS" "$BACKUP_DIR/$(basename "$DEFAULT_USER_SUDOERS").$TIMESTAMP"
    sudo rm -f "$DEFAULT_USER_SUDOERS"
fi

# Re-validate after removal.
sudo visudo -c || die "sudoers validation failed after removing $DEFAULT_USER_SUDOERS — restore from $BACKUP_DIR"

# ── Make /etc files immutable ──────────────────────────────────
log "Setting immutable bit on cage-load-bearing /etc files..."
sudo chattr +i /etc/wsl.conf
sudo chattr +i /etc/fstab
sudo chattr +i /etc/sudoers
# Note: 99-claude-cage is intentionally NOT immutable; edits to the
# allowlist still require sudo (now password-gated), and leaving it
# mutable means you can extend the allowlist with `visudo` rather than
# remembering to chattr -i first.

# ── Done ───────────────────────────────────────────────────────
echo ""
log "=== Cage installed ==="
log "Layer A (interop=false):"
sudo grep -A2 '^\[interop\]' /etc/wsl.conf | sed 's/^/    /'
echo ""
log "Layer B (sudoers cage at $CAGE_FILE):"
sudo cat "$CAGE_FILE" | sed 's/^/    /'
echo ""
log "Immutable files:"
sudo lsattr /etc/wsl.conf /etc/fstab /etc/sudoers | sed 's/^/    /'
echo ""
log "NEXT STEPS:"
log "  1. From Windows PowerShell: wsl --shutdown"
log "  2. Reopen WSL"
log "  3. Run: bash verify-cage.sh"
log "  All bypass attempts in verify-cage.sh must fail."
log ""
log "MANUAL ONE-TIME VERIFICATION (verify-cage.sh cannot do this from"
log "patrick's user because /etc/sudoers is mode 0440):"
log "  sudo lsattr /etc/sudoers"
log "  expected: ----i---------e------- /etc/sudoers"
