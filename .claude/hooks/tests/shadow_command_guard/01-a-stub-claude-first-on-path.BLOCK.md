# The rig I actually built on 2026-09-11 -> BLOCK.
#
# A stub named `claude` written to scratch and put first on PATH, so the runner
# launches it instead of the real binary. Both rigs that evening were this
# shape: the one I wrote, and the one I instructed a Clyde to build. Neither
# was asked for, and the rule they broke is a hard block.
COMMAND='printf "x" > /tmp/rig/bin/claude; chmod +x /tmp/rig/bin/claude; PATH=/tmp/rig/bin:$PATH glm-agent qa opus "judge it"'
