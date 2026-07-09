# Not a feat/ branch -> hook never fires, regardless of missing design docs.
BRANCH="develop"
setup() {
  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
