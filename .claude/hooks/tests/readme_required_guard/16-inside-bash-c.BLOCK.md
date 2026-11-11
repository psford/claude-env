# A shell payload is read like any other command.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  git add -A && git commit -qm "feat: new code"
}
COMMAND='bash -c "gh pr create --base develop --title x --body y"'
