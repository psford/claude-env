# A repo with no README has nothing to keep current.
setup() {
  git rm -q README.md && git commit -qm "no readme"
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  git add -A && git commit -qm "feat: new code"
}
COMMAND='gh pr create --base develop --title "feat: x" --body "y"'
