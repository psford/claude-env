# The spelling that always worked. The control for the two below it: without
# this row, a guard that had stopped seeing commits altogether would still make
# every BLOCK case here fail loudly rather than silently, but nothing would say
# which end broke.
COMMAND='git commit -m "the commit that ate a word: $(whoami)"'
