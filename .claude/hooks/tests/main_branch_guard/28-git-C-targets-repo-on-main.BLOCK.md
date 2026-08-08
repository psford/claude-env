# Session cwd is a feature branch, but -C targets a repo sitting on main.
# The old cwd-only check waved this through -- the false negative. -> BLOCK.
setup() {
  git checkout -q -b feature/local
  git init -q other
  ( cd other && git config user.email t@example.com && git config user.name t \
    && git commit -q --allow-empty -m init && git branch -M main )
}
COMMAND="git -C $PWD/other commit -m x"
