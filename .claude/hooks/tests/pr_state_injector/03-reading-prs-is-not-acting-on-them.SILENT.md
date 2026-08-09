# `gh pr list` IS the PR state. Injecting it into its own output is noise the
# hook explicitly excludes.
COMMAND='gh pr list --state open'
