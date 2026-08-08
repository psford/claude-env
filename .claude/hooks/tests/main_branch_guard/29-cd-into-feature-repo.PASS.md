# A leading `cd` applies to everything after it, so the commit lands in the
# feature-branch repo even though the session sits on main. -> PASS.
setup() {
  git branch -M main
  git init -q other
  ( cd other && git config user.email t@example.com && git config user.name t \
    && git commit -q --allow-empty -m init && git checkout -q -b feature/x )
}
COMMAND="cd $PWD/other && git commit -m x"
