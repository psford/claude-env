# Design doc has an explicit non-placeholder Sign-off line -> PASS.
setup() {
  mkdir -p docs/design-plans
  cat > docs/design-plans/2026-06-26-overview-single-screen.md <<'DOC'
# Overview single-screen design

**Sign-off:** Patrick approved the single-screen layout on 2026-06-26.
DOC
  git add docs/design-plans/2026-06-26-overview-single-screen.md
  git commit -q -m "signed design doc"

  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
