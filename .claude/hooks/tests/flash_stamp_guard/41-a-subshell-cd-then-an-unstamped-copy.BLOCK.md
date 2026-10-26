# a subshell cd then an unstamped copy -> BLOCK.
#
# A cd inside parentheses ends with them. The gate reads every directory the command could
# be in, so a copy judged from the wrong one can't slip through.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
COMMAND='(cd /tmp && ls) && cp firmware/c100/c/build/other.bin out/flash/2-x/DITHERWARE.BIN'
