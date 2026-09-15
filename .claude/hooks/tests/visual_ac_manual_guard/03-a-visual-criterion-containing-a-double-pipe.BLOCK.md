# A visual criterion whose --text carries a double pipe -> BLOCK.
#
# Same defect as 01 and 02, on `||`. At HEAD this passes even though
# "theme" is a visual word.
#
# CE-2.36.
COMMAND='ticket ac add OM-3 --kind automated --text "the theme || the background looks correct"'
