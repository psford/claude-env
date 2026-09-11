# The real file, in the repo that owns it -> PASS.
#
# `glm-agent` resolves on PATH, so a naive name check would refuse every
# legitimate edit to the thing itself -- and a guard that blocks ordinary work
# is one people route around. Inside a work tree, no prepend: neither signal
# fires.
COMMAND='printf "# a comment" >> /home/patrick/projects/claude-harness/plugins/psford-tickets/bin/glm-agent'
