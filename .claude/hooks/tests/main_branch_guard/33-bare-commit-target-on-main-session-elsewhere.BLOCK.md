# The scratch repo sits on main and the command has no `cd` and no `-C`, so the
# only thing that says which repo it means is the payload's cwd. The hook runs
# from a DIFFERENT repo that is on a feature branch, which is how Claude Code
# actually invokes it: the process working directory is the session's repo.
#
# A guard that reads os.getcwd() sees "feature/elsewhere" and allows a commit
# straight onto main. Verified doing exactly that before the fix. -> BLOCK.
setup() {
  git branch -M main
  git init -q ../session-repo
  ( cd ../session-repo && git config user.email t@example.com && git config user.name t \
    && git commit -q --allow-empty -m init && git checkout -q -b feature/elsewhere )
  PROCESS_CWD="$PWD/../session-repo"
}
COMMAND='git commit -m "x"'
