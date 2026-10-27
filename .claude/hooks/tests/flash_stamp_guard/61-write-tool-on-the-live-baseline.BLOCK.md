# write tool on the live baseline -> BLOCK.
#
# The Write tool can't change it either.
TOOL_NAME='Write'
FILE_PATH="$(dirname "$(dirname "$(dirname "$hook")")")/infrastructure/card-folders/card-folder-baseline.json"
CONTENT='{"folders": {}}'
