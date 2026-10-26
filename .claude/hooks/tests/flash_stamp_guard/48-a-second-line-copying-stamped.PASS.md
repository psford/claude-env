# a second line copying stamped -> PASS.
#
# Reading line breaks as separators mustn't refuse an ordinary two-line staging command.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
COMMAND=$'mkdir -p out/flash/2-y\ncp firmware/c100/c/build/probe.bin out/flash/2-y/DITHERWARE.BIN'
