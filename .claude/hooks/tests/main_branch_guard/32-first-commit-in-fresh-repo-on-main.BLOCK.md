# Same unborn-branch situation, but the fresh repo's initial branch is main.
# Being new is not an exemption: the first commit still may not land on trunk.
# -> BLOCK.
setup() {
  git checkout -q -b feature/local         # session repo off main, to isolate the check
  git init -q -b main fresh
}
COMMAND="git -C $PWD/fresh commit -m 'initial'"
