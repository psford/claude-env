# Application code is not infrastructure. A checklist on every commit is noise.
setup() {
  mkdir -p src
  printf 'def main():\n    return 0\n' > src/app.py
  git add src/app.py
}
COMMAND='git commit -m "feat: parse the header"'
