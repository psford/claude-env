# Same hole, the other whitespace. Written with $'\t' so the tab survives being
# read back as a shell variable rather than becoming a space in transit -- a
# fixture that quietly turns into case 01 tests case 01 twice.
COMMAND=$'git\tcommit -m "a tab and a backtick: `whoami`"'
