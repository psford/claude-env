# A real `gh pr create` whose title names no ticket -> PASS.
#
# The known-negative for 02. Without it, a guard that refused every PR would
# satisfy 02 and nothing would notice -- which is the shape this repo has been
# caught by twice tonight.
COMMAND='gh pr create --base main --head develop --title "routine dependency bump"'
