# heredoc script naming out flash -> BLOCK.
#
# A heredoc script that names the folder may write there; text edits go through Edit.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
COMMAND=$'python3 - <<\'EOF\'\nopen("out/flash/2-x/DITHERWARE.BIN", "wb").write(b"x")\nEOF'
