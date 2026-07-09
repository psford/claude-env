# No design docs exist, but the commit command carries the explicit bypass comment -> PASS.
setup() {
  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
COMMAND='git commit -m "css nit" # <!-- DESIGN-SIGNOFF-OK: trivial color tweak -->'
