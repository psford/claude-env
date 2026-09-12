# A bare shell keyword as an ARGUMENT VALUE -> still silent.
#
# Fixture 18 puts its keywords inside quotes, where the mask blanks them, so
# it cannot see a regression of the position-aware head check back to
# checking every unquoted word. This one puts the keyword where the mask
# cannot help: `--to done` is unquoted, and `done` ends a loop somewhere
# else.
#
# That shape is this repo's highest-traffic command -- the daily ticket move
# -- and it regressed exactly once already, during this ticket: the keyword
# scan ran over every unquoted word, so `--to done` made the walk
# non-authoritative and the raw fallback then fired on the note's prose. A
# command that merely NAMES a dispatch was refused, which is the deadlock
# class this chore exists to remove.
#
# Verified RED at 3269217 (the hook spoke where SILENT was expected) by QA
# round 3.
COMMAND='ticket move ZZ-1 --to done --note "why gh workflow run is gated"'
