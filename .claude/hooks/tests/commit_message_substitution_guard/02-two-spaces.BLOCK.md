# CH-237.5 (Grace F10). The trigger was `if "git commit" not in command` -- a
# literal substring with exactly one space -- so this returned 0 and the shell
# ran the substitution into the permanent record.
#
# Bash does not care how much whitespace separates the words. The guard did.
COMMAND='git  commit -m "two spaces and a substitution: $(whoami)"'
