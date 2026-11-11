# -Hbranch and -Bbase are flags too: the named branch is judged, not the checked-out one.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b feature/x
  mkdir -p src
  python3 -c "open('src/app.py','w').write(''.join(f'x{i} = {i}\\n' for i in range(60)))"
  git add -A && git commit -qm "feat: new code"
  git checkout -q -b develop refs/remotes/origin/develop
}
COMMAND='gh pr create -Bdevelop -Hfeature/x --title x --body y'
