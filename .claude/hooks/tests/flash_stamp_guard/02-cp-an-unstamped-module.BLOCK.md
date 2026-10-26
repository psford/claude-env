# cp an unstamped module -> BLOCK.
#
# A build no harness passed. This is the 2026-10-26 failure: probes handed to the camera
# that the checks had not settled.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
COMMAND='cp firmware/c100/c/build/other.bin out/flash/2-x/DITHERWARE.BIN'
