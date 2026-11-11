# --repo names a repo this checkout isn't: its branch can't be seen from here.
setup() {
  git remote add origin git@github.com:psford/ditherware.git
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  printf 'baseline\nx\n' > README.md
  git add -A && git commit -qm "feat: new code, and the README"
}
COMMAND='gh pr create -R psford/other --base develop --title "feat: x" --body "y"'
