# A DRAFT design doc exists (committed) but has no Sign-off/Approved line -> BLOCK.
setup() {
  mkdir -p docs/design-plans
  cat > docs/design-plans/2026-06-26-overview-single-screen.md <<'DOC'
<!-- DRAFT -- pending Patrick's sign-off before implementation -->
# Overview single-screen design

Row-height emphasis boost.
DOC
  git add docs/design-plans/2026-06-26-overview-single-screen.md
  git commit -q -m "wip design doc"

  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
