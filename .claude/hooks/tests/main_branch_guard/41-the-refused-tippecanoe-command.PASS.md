# CE-2.31. The exact command refused on 2026-09-13 -> PASS.
#
# The OM-26.13 vector-tile build: tippecanoe in Docker, run as the invoking
# user so its output is not root-owned. It contains no rm. It carries a
# command substitution, which is why this fix cannot rest on the shell
# parser's all-or-nothing verdict: that parser gives up on "$(...)".
setup() { git checkout -q -b feature/x; }
COMMAND='timeout 590 docker run --rm --user "$(id -u):$(id -g)" -v /tmp/in:/in:ro -v /tmp/out:/out omni-tippecanoe:2.79.0 tippecanoe -o /out/growing-zones.pmtiles -l zones -Z0 -z10 --detect-shared-borders --coalesce-densest-as-needed --extend-zooms-if-still-dropping -y zone -y trange --force /in/gz_v0_raw.json'
