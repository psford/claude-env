# relative paths from a nested cwd -> PASS.
#
# The session's directory is not the repo root: paths resolve against the payload's cwd,
# not the hook's own directory.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
CWD='firmware/c100'
COMMAND='cp c/build/probe.bin ../../out/flash/2-x/DITHERWARE.BIN'
