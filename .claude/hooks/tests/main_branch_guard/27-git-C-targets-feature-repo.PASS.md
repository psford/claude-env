# Session cwd is a repo on main, but -C targets a repo on a feature branch.
# This blocked every commit in every repo of the workspace on 2026-08-07. -> PASS.
setup() {
  git branch -M main
  git init -q other
  ( cd other && git config user.email t@example.com && git config user.name t \
    && git commit -q --allow-empty -m init && git checkout -q -b feature/x )
}
COMMAND="git -C $PWD/other commit -m x"
