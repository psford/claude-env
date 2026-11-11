# A release PR carries features each judged when it opened, so it isn't judged again.
setup() {
  git update-ref refs/remotes/origin/main HEAD
  git checkout -q -b develop
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\n' for i in range(60)))"
  git add -A && git commit -qm "feat: merged features"
}
COMMAND='gh pr create --base main --head develop --title "Release" --body "y"'
