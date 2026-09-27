# Fixture 01's criterion, remedied the way the refusal says -> PASS.
#
# The refusal's first remedy: "it IS about appearance -> add --kind manual".
# Same text as 01, semicolon and all, filed as a manual criterion. The guard
# must let it through, or its own advice deadlocks the rewrite.
#
# CE-2.33.
COMMAND='ticket ac add OM-1 --kind manual --text "the page renders a red badge; the user sees it immediately"'
