# no baseline file -> BLOCK.
#
# Without the baseline nothing unstamped is accepted.
setup() {
  put ditherware 0-stock/GP_CARDVR_UPGRADE.BIN 'stock'
  rm claude-env/infrastructure/card-folders/card-folder-baseline.json
}
EXPECT_MATCH='0-stock/GP_CARDVR_UPGRADE.BIN'
