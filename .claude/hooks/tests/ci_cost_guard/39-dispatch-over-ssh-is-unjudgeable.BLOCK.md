# A dispatch run over ssh -> BLOCK, because it cannot be judged here.
#
# The minutes bill to the same account wherever the `gh` client sits, so this
# is spend either way. What ssh changes is that the repo is on ANOTHER box:
# resolving it against this disk would answer about the wrong machine, and
# this guard's whole judgement is "read that repo's workflows".
#
# So it refuses on the same rule as an unresolvable -R (fixture 28): a repo it
# cannot inspect is not a repo it may approve. The repo here has NO workflows
# at all, which is precisely the state that would otherwise return 0 -- the
# fixture fails if the ssh path silently falls back to judging the local
# directory.
COMMAND="ssh build-box gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1)
