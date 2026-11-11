# A README edit that only changes whitespace isn't an update.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  printf 'baseline   \n\n' > README.md
  git add -A && git commit -qm "feat: new code, README whitespace"
}
COMMAND='gh pr create --base develop --title "feat: x" --body "y"'
