# Control: the same shape of visual criterion, no separators -> BLOCK.
#
# No semicolon, ampersand, pipe or newline anywhere in the command, so
# the segment the guard judges is the whole, correctly-quoted call. This
# already blocks at HEAD; it exists to prove fixtures 01-04 are wrong
# because of the separator alone, not because of some other difference
# in shape. If this one fails, the fixture is wrong -- not the guard.
#
# CE-2.36.
COMMAND='ticket ac add OM-5 --kind automated --text "the badge displays correctly on load"'
