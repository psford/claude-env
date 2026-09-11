# A dispatch split over two lines by a trailing backslash -> BLOCK.
#
# CH-237.9, AC2, and the exact form that returned rc=0 before the fix.
#
# bash DELETES a backslash-newline before it parses anything. posix shlex does
# not: it treats the backslash as an escape, so the newline survives as an
# ordinary character and GLUES ITSELF TO THE NEXT WORD --
#
#   gh \<newline>workflow run ios.yml  ->  ['gh', '\nworkflow', 'run', 'ios.yml']
#
# `rest[:2] == ["workflow", "run"]` is then False and the permanent macOS ban
# does not fire. Nothing about this is exotic; it is how anyone wraps a long
# command. The fix is to join continuations first, which _repo_context.statements
# already does for every other guard in this repo.
#
# $'...' is load-bearing: inside "..." bash would eat the continuation itself
# and the fixture would test the ordinary one-line form by accident.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' \
    > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND=$'gh \\\nworkflow run ios.yml'
