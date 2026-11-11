# Deleting the README isn't a way out of keeping it current.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  git rm -q README.md
  git add -A && git commit -qm "feat: new code, no README"
}
COMMAND='gh pr create --base develop --title "feat: x" --body "y"'
