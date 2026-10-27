# a baseline that is not json -> BLOCK.
#
# A damaged baseline proves nothing: every file it would have covered is refused.
setup() {
  put ditherware 0-stock/GP_CARDVR_UPGRADE.BIN 'stock'
  accept ditherware 0-stock/GP_CARDVR_UPGRADE.BIN
  printf 'not json' > claude-env/infrastructure/card-folders/card-folder-baseline.json
}
EXPECT_MATCH='0-stock/GP_CARDVR_UPGRADE.BIN'
