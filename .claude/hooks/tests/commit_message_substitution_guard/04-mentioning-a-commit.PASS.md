# AC2. Closing a fail-open must not open a false-positive, and this is the case
# that can tell the difference.
#
# A note ABOUT a commit, written into a file. The heredoc is quoted, so the
# shell expands nothing in it -- there is no hazard here at all, only a
# description of one. But the raw command contains the literal substring
# "git commit" and a -m operand with $( ) in double quotes, which is everything
# the old trigger looked for.
#
# This is the family the guard's own docstring describes, and it happened while
# CH-237.5 was being written: a ticket description and a test fixture were both
# refused for containing the phrase. A guard that fires on the mention of a
# thing rather than the thing costs the trust it needs to keep working.
#
# Two earlier drafts of this fixture failed to discriminate -- `git log --grep
# commit` passes under the old code too, and an escaped \" stopped message_args
# matching at all. Neither would have gone red if the fix were reverted, so
# neither was testing this criterion.
COMMAND='cat >> notes.md <<'"'"'EOF'"'"'
the mistake was git commit -m "wip: $(date)" -- the shell ate it
EOF'
