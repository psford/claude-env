# git commit mentioning out flash -> PASS.
#
# Prose about the folder in a commit message is not a write to it (out/ is ignored by git).
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
COMMAND='git commit -m "stage the probe in out/flash/2-x"'
