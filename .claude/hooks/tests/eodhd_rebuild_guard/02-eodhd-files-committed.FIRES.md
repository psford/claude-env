# With the directory present and its files in the commit, it must speak.
setup() {
  mkdir -p eodhd-loader
  printf 'x = 1\n' > eodhd-loader/load.py
  git add -A && git commit -qm "feat: change the loader"
}
COMMAND='git commit -m "feat: change the loader"'
EXPECT_MATCH='.'
