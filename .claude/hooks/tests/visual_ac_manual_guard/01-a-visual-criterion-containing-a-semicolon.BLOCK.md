# A visual criterion whose --text carries a semicolon -> BLOCK.
#
# `_segments` splits the raw command on `;` with no regard for quoting, so
# the semicolon INSIDE this --text value is read as a statement separator.
# The quoted string is torn in half: the first half has an unbalanced
# quote (shlex.split raises, parse fails open), and the second half no
# longer contains `ticket ac add` at all. Neither half is judged, so the
# whole call passes at HEAD even though "renders" is a visual word.
#
# CE-2.36.
COMMAND='ticket ac add OM-1 --kind automated --text "the page renders a red badge; the user sees it immediately"'
