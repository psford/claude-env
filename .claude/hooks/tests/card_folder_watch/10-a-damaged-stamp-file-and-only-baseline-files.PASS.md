# a damaged stamp file and only baseline files -> SILENT.
#
# The baseline still covers what it accepted.
setup() {
  put ditherware 0-stock/GP_CARDVR_UPGRADE.BIN 'stock'
  accept ditherware 0-stock/GP_CARDVR_UPGRADE.BIN
  mkdir -p ditherware/firmware/c100/c/build
  printf 'not json' > ditherware/firmware/c100/c/build/emulator-passed.json
}
