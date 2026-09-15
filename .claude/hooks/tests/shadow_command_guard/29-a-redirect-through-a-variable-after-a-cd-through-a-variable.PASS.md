# A cd through a variable, redirecting to a path held in a variable,
# from a session inside a tests directory -> PASS.
#
# CE-2.39, second instance. The session's own cwd is nested inside a tests
# directory (via the driver's CWD setting). The command moves out of it with
# `cd "$W"` and redirects into a path named by `$S` -- the guard cannot
# follow `cd $W` at all (it is not a real directory until expanded), so the
# shell never appears to leave the session's tests directory, and the
# unexpanded `$S/log.txt` reads as a new directory under it.
#
# The same command with a literal `cd` (fixture 28, and every other fixture
# in this suite) already passes; this is the same command with both the cd
# target and the redirect target held in variables assigned earlier in the
# same command string.
setup() {
  mkdir -p tests/sub
  mkdir -p real_dir
}
TOOL_NAME="Bash"
COMMAND='W=../../real_dir; S=out; cd "$W" && bash run-hook-tests.sh > "$S/log.txt"'
CWD="tests/sub"
