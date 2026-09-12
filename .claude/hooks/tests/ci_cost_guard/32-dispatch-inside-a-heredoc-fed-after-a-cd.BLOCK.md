# A dispatch inside a heredoc fed to a shell AFTER a cd -> BLOCK.
#
# CH-237.10, defect 3. FEEDS_CODE is anchored to the START of the line, and
# the feeder line begins with `cd <ios> &&`, so the body was dropped as data.
# Real bash cds and then executes it. The cd must move the target AND the
# heredoc body must be read as the code it is.
#
# $'...' is load-bearing: the fixture needs a real newline for the heredoc.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t )
  mkdir -p ios/.github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND=$'cd ios && bash <<\'EOF\'\ngh workflow run ios.yml\nEOF'
ENV_VARS=(CI_RUN_OK=1)
