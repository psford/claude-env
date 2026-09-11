# Text that DESCRIBES a shadow is not one -> PASS.
#
# The specificity control for 12, and the one that matters most: a guard that
# refused any command mentioning a redefinition would block the act of
# recording this very defect on its own ticket. That deadlock is not
# hypothetical either -- it is the whole subject of CE-2.20, where a guard
# read a sentence about a dispatch as a dispatch and stopped the CSO gate.
#
# Quoted regions are masked before the scan, so the definition below is seen
# as the argument text it is.
TOOL_NAME="Bash"
COMMAND='ticket attach-evidence CE-2.19 --summary "I used a cd() { :; } prefix to slip past the guard"'
