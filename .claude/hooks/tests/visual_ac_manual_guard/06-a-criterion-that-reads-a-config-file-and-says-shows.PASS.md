# An automated criterion that names a config file's contents, worded with
# "shows" -> PASS (not refused).
#
# "shows" is an everyday verb here, not a report of what someone saw on a
# rendered page: the criterion names the exact file being read and what its
# contents are. At HEAD this is refused solely because "shows" is a word on
# the visual list -- the guard cannot tell this apart from a report of what
# a person watched happen on screen. It should not be refused: it names a
# file's contents, one of the things `ticket ac add`'s own AC1 calls out as
# still-automated regardless of the everyday verb used to describe it.
#
# CE-2.38.
COMMAND='ticket ac add OM-6 --kind automated --text "Reading vite.config.ts shows vitest'"'"'s default excludes kept, not replaced"'
