# A test file renamed and edited stays a test file. The first version read the
# rename's path as `b.py` and counted it as code (cold review, 2026-11-10).
setup() {
  mkdir -p tests
  python3 -c "open('tests/test_a.py','w').write(''.join(f'def test_{i}(): pass\n' for i in range(80)))"
  git add -A && git commit -qm "tests"
  git update-ref refs/remotes/origin/develop HEAD
  git checkout -q -b test/rename
  git mv tests/test_a.py tests/test_b.py
  python3 -c "open('tests/test_b.py','a').write(''.join(f'def test_more_{i}(): pass\n' for i in range(70)))"
  git add -A && git commit -qm "test: rename and extend"
}
COMMAND='gh pr create --base develop --title "test: rename" --body "y"'
