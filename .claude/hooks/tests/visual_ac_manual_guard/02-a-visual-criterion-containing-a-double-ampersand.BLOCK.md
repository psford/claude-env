# A visual criterion whose --text carries a double ampersand -> BLOCK.
#
# Same defect as 01, on `&&`: it is data inside the quoted --text value,
# but `_segments` treats it as a statement separator regardless of
# quoting and tears the argument in two. At HEAD this passes even though
# "display" is a visual word.
#
# CE-2.36.
COMMAND='ticket ac add OM-2 --kind automated --text "the badge && the icon both display correctly"'
