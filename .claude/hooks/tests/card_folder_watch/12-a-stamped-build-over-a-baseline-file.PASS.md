# a stamped build over a baseline file -> SILENT.
#
# Replacing an accepted file with stamped bytes is the way forward, not a breach.
setup() {
  put ditherware 5-fullres/DITHERWARE.BIN 'old'
  accept ditherware 5-fullres/DITHERWARE.BIN
  put ditherware 5-fullres/DITHERWARE.BIN 'verified'
  stamp ditherware ditherware/out/flash/5-fullres/DITHERWARE.BIN
}
