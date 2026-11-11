# Documentation and tests aren't code the README describes, however much of them moves.
setup() {
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b test/more
  mkdir -p tests docs src
  python3 -c "open('tests/test_app.py','w').write(''.join(f'def test_{i}(): pass\n' for i in range(80)))"
  python3 -c "open('docs/guide.md','w').write(''.join(f'line {i}\n' for i in range(80)))"
  python3 -c "open('src/app.test.js','w').write(''.join(f'test({i});\n' for i in range(80)))"
  git add -A && git commit -qm "test: more"
}
COMMAND='gh pr create --base develop --title "test: more" --body "y"'
