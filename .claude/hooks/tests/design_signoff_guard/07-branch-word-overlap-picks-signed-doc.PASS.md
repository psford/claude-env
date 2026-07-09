# Two design docs exist; only the one whose filename overlaps the branch slug is signed off -> PASS.
BRANCH="feat/emphasis-sizing-v2"
setup() {
  mkdir -p docs/design-plans
  cat > docs/design-plans/2026-05-01-unrelated-nav-redesign.md <<'DOC'
# Nav redesign
DOC
  cat > docs/design-plans/2026-07-01-emphasis-sizing.md <<'DOC'
# Emphasis sizing design

**Approved:** Patrick approved emphasis sizing v2 on 2026-07-01.
DOC
  git add docs/design-plans/
  git commit -q -m "design docs"

  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
