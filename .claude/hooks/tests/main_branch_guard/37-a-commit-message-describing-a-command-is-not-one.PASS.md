# CE-2.29. A heredoc commit message that DESCRIBES a destructive command -> PASS.
#
# The feeder line holds two statements and only the second is fed the body.
# _body_can_run used to ask every statement on the line, so the unrelated
# `git add` decided the MESSAGE was code, and a commit describing the fix to
# this very guard was refused twice. The statement carrying `<<MARKER` is the
# one being fed, and `git commit -F -` takes the body as text.
setup() { git checkout -q -b feature/x; }
COMMAND=$'git add guard.py && git commit -q -F - <<\'MSG\'\nfix: the git clean -f pattern no longer reads a filename as a flag\nMSG'
