# CE-2.31. Docker's --rm with a later --force belonging to another program -> PASS.
#
# `\brm` matched the rm inside `--rm` (a word boundary sits between "-" and
# "r"), and the flag search then took an r and an f from anywhere after it.
# Any `docker run --rm` whose arguments carried a flag with an f in it read as
# rm -rf. --rm is a flag, not a command.
setup() { git checkout -q -b feature/x; }
COMMAND='docker run --rm omni-tippecanoe:2.79.0 tippecanoe -o /out/x.pmtiles --force /in/x.json'
