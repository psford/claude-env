# cp from a session cwd inside out -> PASS.
#
# A path that reaches the folder without spelling out/flash is still recognised, and a stamped one passes.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
CWD='out'
COMMAND='cp ../firmware/c100/c/build/probe.bin flash/2-x/DITHERWARE.BIN'
