# Staged files have nothing to do with docs/implementation-plans -> hook exits early, PASS.
setup() {
  printf 'notes\n' > README.md
  git add README.md
}
