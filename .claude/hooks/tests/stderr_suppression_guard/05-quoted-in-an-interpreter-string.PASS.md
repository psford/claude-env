# A suppression inside `python3 -c "..."` is a STRING, not a redirect.
#
# Found by being blocked twice within five minutes of activating this guard, on
# tooling that suppressed nothing. This guard deliberately does NOT use
# scannable_text, which keeps interpreter -c bodies intact — correct for guards
# about what a command DOES, wrong for one whose subject is redirect syntax.
#
# Residual gap, deliberate: a one-liner that shells out with suppression is now
# missed. A guard that fires on every python heredoc gets switched off, and then
# it catches nothing at all.
COMMAND="python3 -c \"needle = 'tr a b 2>/dev/null'\""
