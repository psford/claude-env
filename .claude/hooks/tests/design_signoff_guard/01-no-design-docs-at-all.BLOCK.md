# feat/ branch stages a visual-surface file but no docs/design-plans/*.md exists at all -> BLOCK.
setup() {
  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
