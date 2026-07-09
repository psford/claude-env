# A 5-line untracked file removed via `rm` is well under threshold -> PASS.
setup() {
  printf 'one\ntwo\nthree\nfour\nfive\n' > small.txt
}
COMMAND="rm small.txt"
