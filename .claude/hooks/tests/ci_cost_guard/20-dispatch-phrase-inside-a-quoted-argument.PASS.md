# The dispatch phrase inside a quoted ARGUMENT -> PASS.
#
# CE-2.8, third defect. DISPATCH_RE matched the raw command, so writing the
# phrase as data fired the guard. Twice for real while building this ticket:
#
#   ticket ac add CE-2.8 --text "...the dispatch phrase..."   -> BLOCKED
#   a heredoc writing a fixture whose COMMAND= held it        -> BLOCKED
#
# Neither runs anything on GitHub. One was a ticket description and one was a
# test fixture, and both were refused as attempts to spend money.
#
# A guard that fires on the MENTION of a thing rather than the thing spends the
# trust it needs to keep working — the way past a guard that cries wolf is to
# stop reading it. Same family as CH-192.2, where an unexpanded `$var` in a path
# made a guard judge the wrong repo: both are the cost of reading a command as
# text rather than as a command.
#
# The repo has a macOS workflow, so the macOS path is live and only the parsing
# keeps this from blocking.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  workflow_dispatch:\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="echo 'the ban on gh workflow run is permanent'"
