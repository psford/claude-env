# The first commit in a brand-new repo: the branch is *unborn*, so
# `rev-parse --abbrev-ref HEAD` fails while `branch --show-current` reports it.
# Reading the branch with rev-parse made every new repo's first commit
# impossible once undetectable branches began failing closed. -> PASS.
setup() {
  git branch -M main                       # session repo sits on main
  git init -q -b feature/work fresh        # target: created, never committed to
}
COMMAND="git -C $PWD/fresh commit -m 'initial'"
