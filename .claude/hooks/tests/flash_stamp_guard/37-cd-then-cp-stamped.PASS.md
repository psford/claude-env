# cd then cp stamped -> PASS.
#
# The command moves first: its paths are relative to where it cd's, not the session's
# directory. Found live on 2026-10-26: the hook judged them against the session's directory.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
  h=$(sha256sum firmware/c100/c/build/probe.bin | cut -d' ' -f1)
  printf '{"stamps": {"%s": {"file": "firmware/c100/c/build/probe.bin", "harness": "emu_dsp_probe.py"}}}\n' "$h" \
    > firmware/c100/c/build/emulator-passed.json
}
CWD='firmware'
COMMAND="cd $PWD && cp firmware/c100/c/build/probe.bin out/flash/2-x/DITHERWARE.BIN"
