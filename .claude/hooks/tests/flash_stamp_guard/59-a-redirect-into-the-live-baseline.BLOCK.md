# a redirect into the live baseline -> BLOCK.
#
# card_folder_watch reads the baseline from this checkout; changing it is a PR, not a write.
# The live copy is the one beside this hook ($hook is the hook under test).
COMMAND="echo {} > $(dirname "$(dirname "$(dirname "$hook")")")/infrastructure/card-folders/card-folder-baseline.json"
