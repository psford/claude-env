# a module changed after its stamp -> BLOCK.
#
# The stamp is for bytes, not a file name: an edit after the harness ran voids it.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
  printf 'edited\\n' >> firmware/c100/c/build/probe.bin
}
COMMAND='cp firmware/c100/c/build/probe.bin out/flash/2-x/DITHERWARE.BIN'
