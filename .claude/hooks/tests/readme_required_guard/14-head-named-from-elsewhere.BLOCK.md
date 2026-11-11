# --head names the branch: it's judged even when another branch is checked out.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  git add -A && git commit -qm "feat: new code"
  git checkout -q -b develop refs/remotes/origin/develop
}
COMMAND='gh pr create --base develop --head feature/x --title "feat: x" --body "y"'
