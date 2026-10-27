# a baseline file removed -> SILENT.
#
# Removing a file stages nothing.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'old'
  accept ditherware 2-x/DITHERWARE.BIN
  rm ditherware/out/flash/2-x/DITHERWARE.BIN
}
