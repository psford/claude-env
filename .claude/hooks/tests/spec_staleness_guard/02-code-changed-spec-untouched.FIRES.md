# The case it exists for: a feature branch whose code moved while the spec did
# not. Needs origin/main to diff against and a branch that is not main/develop —
# all three are the hook's real preconditions, so the fixture builds them rather
# than hoping.
setup() {
  mkdir -p docs src
  printf '# Technical Spec\nHow it works.\n' > docs/TECHNICAL_SPEC.md
  printf 'def f():\n    return 1\n' > src/app.py
  git add -A && git commit -qm "feat: spec and code"
  git update-ref refs/remotes/origin/main HEAD
  git checkout -q -b feature/changes
  # Enough added lines to clear NEW_LINES_THRESHOLD — the hook ignores small
  # diffs on purpose, so a two-line fixture would pass as SILENT and record
  # the hook as broken when it was behaving correctly.
  python3 -c "open('src/app.py','w').write(''.join(f'def f{i}():\n    return {i}\n' for i in range(60)))"
  git add -A && git commit -qm "feat: change the behavior without touching the spec"
}
COMMAND='git push origin feature/changes'
EXPECT_MATCH='spec|TECHNICAL_SPEC'
