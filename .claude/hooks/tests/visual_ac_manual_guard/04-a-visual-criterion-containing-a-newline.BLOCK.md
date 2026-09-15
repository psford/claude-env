# A visual criterion whose --text carries a newline -> BLOCK.
#
# `_segments` also splits on `\n`, so a literal newline embedded in the
# --text value (ANSI-C quoting puts a real newline byte in COMMAND, not
# an escape) tears the quoted argument across two segments exactly as 01
# through 03 do on their own separators. At HEAD this passes even though
# "layout" is a visual word.
#
# CE-2.36.
COMMAND=$'ticket ac add OM-4 --kind automated --text "the layout\nlooks broken on mobile"'
