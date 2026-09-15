# A file read before a `cd` into a tests directory -> PASS.
#
# CE-2.39, first instance. The read happens in a python3 -c payload BEFORE
# the cd; the guard resolves it AFTER, because resolve() used the command's
# single, final directory for every candidate regardless of which statement
# actually named it. `src/config.json` lives at the repo root; joined
# against the post-cd directory it becomes `tests/src/config.json`, which
# does not exist and sits under a "tests" segment -- read as a new test
# root being built, though nothing is being built at all.
#
# `tests` here is a fresh, driver-less directory the command itself is not
# creating -- unlike .claude/hooks/tests, it holds no runner, so
# inside_an_established_suite cannot rescue the wrong answer by finding one
# on the way up.
setup() {
  mkdir -p tests
  mkdir -p src
  printf '{}' > src/config.json
}
TOOL_NAME="Bash"
COMMAND="python3 -c 'import json; json.load(open(\"src/config.json\"))' && cd tests && bash run-hook-tests.sh"
