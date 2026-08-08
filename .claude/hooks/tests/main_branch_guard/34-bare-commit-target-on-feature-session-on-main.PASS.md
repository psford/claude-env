# The mirror, so the fix cannot be "always block". The target repo is on a
# feature branch; the session repo happens to sit on main. Reading the process
# cwd here would block legitimate work, which is how a guard gets disabled.
# -> PASS.
setup() {
  git checkout -q -b feature/real-work
  git init -q ../session-repo
  ( cd ../session-repo && git config user.email t@example.com && git config user.name t \
    && git commit -q --allow-empty -m init && git branch -M main )
  PROCESS_CWD="$PWD/../session-repo"
}
COMMAND='git commit -m "x"'
