# No --base, so the base is origin's default branch (here a trunk repo's main), and the
# feature is judged against it.
setup() {
  git update-ref refs/remotes/origin/main HEAD
  git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\n' for i in range(60)))"
  git add -A && git commit -qm "feat: new code"
}
COMMAND='gh pr create --title "feat: x" --body "y"'
