# No --base and no origin/HEAD: the guard can't tell what the PR is against, so it refuses.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  printf 'baseline\nx\n' > README.md
  git add -A && git commit -qm "feat: new code, and the README"
}
COMMAND='gh pr create --title "feat: x" --body "y"'
