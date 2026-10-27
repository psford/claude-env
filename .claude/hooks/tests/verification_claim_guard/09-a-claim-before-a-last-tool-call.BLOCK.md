# a claim before a last tool call -> BLOCK.
#
# The reply's text sits in an earlier assistant entry than its last tool call; the guard
# reads back to the last text, not just the last entry.
MESSAGE='It is fixed and it works now.'
TOOL_CALL_AFTER=1
