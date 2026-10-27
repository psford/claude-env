# no card folder anywhere -> SILENT.
#
# Projects without an out/flash/ are not the watch's business.
setup() {
  mkdir -p road-trip/src
  printf 'x' > road-trip/src/app.js
}
