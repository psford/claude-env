#!/usr/bin/env bash
# verify-cage.sh
#
# Attempts every known bypass against the WSL sandbox cage.
# Every "block" attempt MUST be blocked. Any PASS that succeeds means
# the cage has a hole.
#
# IMPORTANT: This script is non-destructive. Tests use benign targets
# (nonexistent files, /dev/null) so even if the cage is broken and sudo
# passes through, no damage occurs. Earlier versions ran destructive
# commands directly (chattr -i /etc/wsl.conf, tee /etc/wsl.conf, etc.)
# which actively dismantled the cage when it wasn't holding.

set +e  # we WANT non-zero exits in attempts; collect them all

PASS=0
FAIL=0
RED=$'\e[31m'
GRN=$'\e[32m'
YLW=$'\e[33m'
RST=$'\e[0m'

# Helper: assert that running `sudo -n <cmd>` is BLOCKED by the cage
# (i.e. sudo says "password required"). Uses benign target args.
assert_sudo_blocked() {
    local desc="$1"; shift
    local out rc
    out=$(timeout 5 "$@" 2>&1 </dev/null)
    rc=$?
    if echo "$out" | grep -qE 'a password is required'; then
        echo "${GRN}PASS${RST}: $desc -- sudo blocked (password required)"
        PASS=$((PASS+1))
    else
        echo "${RED}FAIL${RST}: $desc -- sudo passed through (rc=$rc)"
        echo "       output: $(echo "$out" | head -1)"
        FAIL=$((FAIL+1))
    fi
}

# Helper: assert direct execution (no sudo) of <cmd> fails.
assert_direct_blocked() {
    local desc="$1"; shift
    local rc
    timeout 5 "$@" >/dev/null 2>&1
    rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "${GRN}PASS${RST}: $desc -- blocked (rc=$rc)"
        PASS=$((PASS+1))
    else
        echo "${RED}FAIL${RST}: $desc -- succeeded (rc=0) but should have been blocked"
        FAIL=$((FAIL+1))
    fi
}

# Helper: assert <cmd> succeeds (positive check).
assert_allowed() {
    local desc="$1"; shift
    local out rc
    out=$(timeout 5 "$@" 2>&1)
    rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "${GRN}PASS${RST}: $desc -- allowed as expected"
        PASS=$((PASS+1))
    else
        echo "${RED}FAIL${RST}: $desc -- failed (rc=$rc): $(echo "$out" | head -1)"
        FAIL=$((FAIL+1))
    fi
}

# Helper: assert a file currently has a specific lsattr flag set.
assert_lsattr_flag() {
    local desc="$1" file="$2" flag="$3"
    if lsattr "$file" 2>/dev/null | head -1 | awk '{print $1}' | grep -q "$flag"; then
        echo "${GRN}PASS${RST}: $desc"
        PASS=$((PASS+1))
    else
        echo "${RED}FAIL${RST}: $desc -- $flag flag missing on $file"
        FAIL=$((FAIL+1))
    fi
}

NX=/tmp/__verify_cage_nonexistent_$$__   # nonexistent file used as benign target

echo "=== verify-cage.sh ==="
echo

echo "${YLW}--- Layer A: WSL interop disabled ---${RST}"
assert_direct_blocked "powershell.exe blocked" /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -Command Get-Date
assert_direct_blocked "cmd.exe blocked"        /mnt/c/Windows/System32/cmd.exe /c echo hi
assert_direct_blocked "wsl.exe blocked"        /mnt/c/Windows/System32/wsl.exe -l
# shellcheck disable=SC2016 # $x expands in inner bash, intentional
assert_direct_blocked "any /mnt/c .exe blocked" \
    bash -c 'for x in /mnt/c/Windows/System32/notepad.exe /mnt/c/Windows/explorer.exe; do "$x" >/dev/null 2>&1 && exit 0; done; exit 1'

echo
echo "${YLW}--- Layer B: sudo password-gated (non-destructive probes) ---${RST}"
# All tests use sudo -n with benign targets. If cage holds, sudo blocks
# with "password required". If cage is broken, sudo passes through and
# the underlying command fails on the benign target without damage.
assert_sudo_blocked "sudo true requires password"           sudo -n true
assert_sudo_blocked "sudo whoami requires password"          sudo -n whoami
assert_sudo_blocked "sudo apt-get requires password"         sudo -n apt-get --version
assert_sudo_blocked "sudo cat (any file) requires password"  sudo -n cat /dev/null
assert_sudo_blocked "sudo mount requires password"           sudo -n mount --help
assert_sudo_blocked "sudo umount requires password"          sudo -n umount "$NX"
assert_sudo_blocked "sudo chattr requires password"          sudo -n chattr +i "$NX"
assert_sudo_blocked "sudo sed requires password"             sudo -n sed -i s/x/y/ "$NX"
assert_sudo_blocked "sudo tee requires password"             sudo -n tee /dev/null
assert_sudo_blocked "sudo visudo requires password"          sudo -n visudo -c

echo
echo "${YLW}--- Layer B: critical /etc files are immutable + unwritable ---${RST}"
assert_lsattr_flag "/etc/wsl.conf has chattr +i"  /etc/wsl.conf  i
assert_lsattr_flag "/etc/fstab has chattr +i"     /etc/fstab     i
# /etc/sudoers chattr is not patrick-readable (mode 0440 root-only) and
# lsattr is intentionally NOT in the NOPASSWD allowlist. The "patrick
# cannot modify /etc/sudoers" property is covered by the perms+cage tests
# below; chattr +i is a root-compromise defense, verify manually as root.
# Direct user writes to /etc files (no sudo) -- should fail on permissions
assert_direct_blocked "Append /etc/wsl.conf as user (no sudo)" bash -c 'echo x >> /etc/wsl.conf'
assert_direct_blocked "Append /etc/fstab as user (no sudo)"    bash -c 'echo x >> /etc/fstab'
assert_direct_blocked "Append /etc/sudoers as user (no sudo)"  bash -c 'echo x >> /etc/sudoers'
assert_direct_blocked "Write cage file as user (no sudo)"      bash -c 'echo x > /etc/sudoers.d/zz-claude-cage'

echo
echo "${YLW}--- Positive checks: legitimate operations still work ---${RST}"
# shellcheck disable=SC2016 # $$, $F expand in inner bash, intentional
assert_allowed "Carve-out write succeeds" \
    bash -c 'F=/mnt/c/Users/patri/Documents/claudeProjects/projects/_cage_test_$$.txt; touch "$F" && rm "$F"'
# shellcheck disable=SC2016
assert_direct_blocked "Other /mnt/c paths still ro" \
    bash -c 'F=/mnt/c/Users/patri/Documents/_should_fail_$$.txt; touch "$F"'
assert_allowed "NOPASSWD allowlist (journalctl)" sudo -n journalctl -n 1
assert_allowed "NOPASSWD allowlist (dmesg)"      sudo -n dmesg

echo
echo "=== Summary ==="
echo "Passed: ${GRN}${PASS}${RST}"
echo "Failed: ${RED}${FAIL}${RST}"
if [[ $FAIL -eq 0 ]]; then
    echo "${GRN}Cage holds.${RST}"
    exit 0
else
    echo "${RED}Cage has gaps. Investigate failures above before trusting the sandbox.${RST}"
    exit 1
fi
