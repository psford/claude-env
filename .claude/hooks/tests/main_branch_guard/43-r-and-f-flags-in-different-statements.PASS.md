# CE-2.31. An r flag on rm and an f flag on a later command -> PASS.
#
# The flag search walked every word after the rm, across `&&`, `;` and `|`,
# so an -r in one statement and a --force in the next combined into rm -rf.
# `rm -r build` without force is not what this check refuses, and a flag
# belongs to the command it is written after.
setup() { git checkout -q -b feature/x; }
COMMAND='rm -r build && tippecanoe --force x.json'
