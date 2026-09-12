# A definition carried in a quoted `eval` payload -> BLOCK.
#
# The main scan masks quoted regions so prose describing a definition
# is not read as making one (fixture 13). That protection also hid
# every interpreter payload. A payload is quoted AND it is code, and
# code gets read -- the same distinction strip_heredoc_bodies already
# draws for heredocs.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='eval '\''cd() { :; }'\'''
