# The documented way out, and it must keep working: single quotes are literal,
# so the shell substitutes nothing and git receives the backticks as typed.
# The guard's own refusal text offers this, so a guard that refused it would be
# giving instructions it does not honour.
COMMAND="git commit -m 'a backtick \`like this\` survives single quotes'"
