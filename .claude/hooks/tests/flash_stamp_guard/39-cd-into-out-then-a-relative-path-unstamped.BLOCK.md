# cd into out then a relative path, unstamped -> BLOCK.
#
# The hole the live test exposed: after cd into out/, "flash/2-x/..." never spells
# out/flash, and read from the session's directory it lands nowhere near the card folder.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
CWD='firmware'
COMMAND="cd $PWD/out && cp ../firmware/c100/c/build/other.bin flash/2-x/DITHERWARE.BIN"
