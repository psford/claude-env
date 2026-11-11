# A lock file and a binary aren't code the README describes.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b chore/deps
  python3 -c "open('package-lock.json','w').write(''.join(f'\"dep{i}\": \"1.0.{i}\",\n' for i in range(200)))"
  python3 -c "open('logo.png','wb').write(bytes(range(256)) * 40)"
  git add -A && git commit -qm "chore: deps"
}
COMMAND='gh pr create --base develop --title "chore: deps" --body "y"'
