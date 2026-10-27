# reading the live baseline -> PASS.
#
# Reading writes nothing.
COMMAND="cat $(dirname "$(dirname "$(dirname "$hook")")")/infrastructure/card-folders/card-folder-baseline.json"
