# A real commit with nothing for the shell to substitute. The discriminating
# control: every BLOCK case above is also a real commit, so without this row a
# guard that refused all commits outright would look perfect.
COMMAND='git  commit -m "fix(CE-1): two spaces, and nothing to expand"'
