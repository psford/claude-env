# --repo naming this checkout's own repo is judged as usual, and passes with the README.
setup() {
  git remote add origin https://github.com/psford/ditherware.git
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  printf 'baseline\nx\n' > README.md
  git add -A && git commit -qm "feat: new code, and the README"
}
COMMAND='gh pr create --repo psford/ditherware --base develop --title "feat: x" --body "y"'
