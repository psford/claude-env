# A file named after a real command, inside a git work tree, at a path that is
# NOT where that command lives -> PASS.
#
# This pins the work-tree discriminator, and it exists because nothing else
# did. Fixture 04 looked like it covered this and does not: `which glm-agent`
# resolves to exactly the path 04 writes to, so 04 exercises the "this IS the
# real file" branch and returns before the work-tree question is ever asked.
# Mutating in_a_work_tree to always answer False left all seven earlier
# fixtures green -- a discriminator nothing could see.
#
# `ticket` is the right name to use here: it resolves on PATH (to the
# installed shim), so the name genuinely collides, and this path is plainly
# not it. A project file that happens to share a command's name is ordinary,
# and refusing it would be the false positive that gets a guard routed around.
COMMAND='printf "notes about the CLI" > /home/patrick/projects/claude-env/docs/ticket'
