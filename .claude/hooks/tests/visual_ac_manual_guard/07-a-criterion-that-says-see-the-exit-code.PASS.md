# An automated criterion that names an exit code, worded with "see" and
# "look" -> PASS (not refused).
#
# Both words are everyday usage for reading a terminal, not for watching a
# rendered page: the criterion names the concrete, machine-checkable thing
# it is judging -- the process's exit code. At HEAD "look" alone is enough
# to refuse this (it is on the visual-word list with no way to tell "look
# at the exit code" from "look at how the theme looks"), and the fix must
# not swap that for a bare "see" doing the same wrong thing.
#
# CE-2.38.
COMMAND='ticket ac add OM-7 --kind automated --text "Look in the terminal after the guard runs: you see its exit code, 0 when the criterion is allowed and 2 when it is blocked."'
