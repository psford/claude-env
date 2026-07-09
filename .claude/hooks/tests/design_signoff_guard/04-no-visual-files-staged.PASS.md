# feat/ branch, but the staged files aren't visual-surface -> hook doesn't even look for a design doc.
setup() {
  printf 'notes\n' > NOTES.md
  git add NOTES.md
}
