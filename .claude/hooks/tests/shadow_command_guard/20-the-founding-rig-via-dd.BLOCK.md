# The same rig via `dd` -> BLOCK.
#
# dd names its destination with `of=` rather than by position, so a
# positional read of the last token sees a flag and nothing else.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='dd if=/tmp/stub/claude of=/tmp/rig/bin/claude && PATH=/tmp/rig/bin:$PATH glm-agent qa opus judge'
