# Control: a criterion about what someone sees on a rendered page -> still
# BLOCK.
#
# Same everyday word as fixture 06 ("shows"), but this criterion names no
# file, command, exit code or test -- it reports what appears in a browser.
# This already blocks at HEAD; it exists to prove that fixtures 06-08 pass
# because they name what they check, not because the fix stopped judging
# "shows"/"see"/"look"/"displays" at all. If this one stops blocking, the
# fix over-corrected -- not the guard.
#
# CE-2.38.
COMMAND='ticket ac add OM-9 --kind automated --text "Opening the app in the browser, the dashboard page shows a red banner across the top"'
