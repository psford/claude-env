# The same stub, with PATH set in some later command -> still BLOCK.
#
# The prepend is not what makes it a shadow; being a `claude` that is not THE
# claude is. A rule demanding both signals in one command would be satisfied by
# pressing enter twice.
COMMAND='printf "#!/bin/sh" > /tmp/rig/claude'
