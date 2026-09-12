# A title whose text happens to contain shell keywords -> still allowed.
#
# The second known-negative. `if`, `while`, `time` and `do` are ordinary
# English words, and a guard that treats every occurrence as a shell keyword
# refuses prose for a living -- which is the defect this ticket opened on.
#
# The keyword scan runs over text with quoted spans blanked, so a keyword
# inside an argument is invisible to it. That is the whole distinction: a
# keyword in COMMAND position introduces a command, a keyword in a quoted
# argument is a word in a sentence.
COMMAND='ticket new --type chore --title "decide if we run the workflow while the ban holds"'
