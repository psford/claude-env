# An automated criterion that names a command's output, worded with
# "displays" -> PASS (not refused).
#
# "displays" here describes what a command prints to the terminal, not
# what a person watched appear on a rendered page. The criterion names the
# command and the count it is judging. At HEAD this is refused solely
# because "displays" is a word on the visual list.
#
# CE-2.38.
COMMAND='ticket ac add OM-8 --kind automated --text "Running the count command displays 3, matching the number of fixtures the directory now holds"'
