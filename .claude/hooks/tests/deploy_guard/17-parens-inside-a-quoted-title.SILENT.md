# A ticket title containing parens AND the words -> still allowed.
#
# The known-negative for fixtures 11-16, and it caught a real regression while
# this was being written. The first masking pass kept bare parens visible
# inside double quotes, so this title read as a subshell, fell back to the raw
# text match, and was refused -- reintroducing the exact false positive CE-2.20
# exists to remove, as the fix for its opposite.
#
# Inside double quotes `(` is an ordinary character. Only `$(` and a backtick
# stay live there, which is why those two are kept and the paren is not.
#
# Without this fixture, a guard that refused every parenthesis would satisfy
# 11-16 and nothing would notice.
COMMAND='ticket new --type chore --title "why (gh workflow run) is gated"'
