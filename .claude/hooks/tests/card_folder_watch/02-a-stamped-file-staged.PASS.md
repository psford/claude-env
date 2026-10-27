# a stamped file staged -> SILENT.
#
# Bytes an emulator harness passed may be in the card folder, however they got there.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'probe'
  stamp ditherware ditherware/out/flash/2-x/DITHERWARE.BIN
}
