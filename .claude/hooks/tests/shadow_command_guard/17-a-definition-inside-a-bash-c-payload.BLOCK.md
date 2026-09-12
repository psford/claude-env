# The same payload through `bash -c` -> BLOCK.
#
# Reaching for a different interpreter is the shape of every evasion
# this repo has recorded, so sh -c and the function-keyword spelling
# are covered by the same walk rather than by three regexes.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='bash -c '\''function cd { :; }'\'''
