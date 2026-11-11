# Under the 50-line bar Patrick chose: a small fix needs no README change.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b fix/typo
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\n' for i in range(20)))"
  git add -A && git commit -qm "fix: small"
}
COMMAND='gh pr create --base develop --title "fix: small" --body "y"'
