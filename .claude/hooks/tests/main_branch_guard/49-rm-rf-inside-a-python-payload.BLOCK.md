# CE-2.31. rm -rf inside an interpreter's -c payload -> BLOCK.
#
# scannable_text keeps an interpreter's -c statement whole because it is code
# wearing a string's clothes. Reading rm only as a command word must still see
# it there: `'rm` follows a quote, not a hyphen.
setup() { git checkout -q -b feature/x; }
COMMAND=$'python3 -c "import os; os.system(\'rm -rf build\')"'
EXPECT_MATCH="rm -rf is forbidden"
