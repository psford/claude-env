# `echo '...' | bash` -> the hard deny still fires.
#
# The dispatch text is an ARGUMENT to echo, which is data, and `bash` reads it
# from stdin, which no token walk can follow. Both halves look innocent alone;
# the pipe is what makes them an instruction.
#
# Nothing here pretends to trace the data. A pipeline whose sink is a shell is
# simply something this parser cannot see into, so it stops claiming to have
# looked and the caller falls back -- the same answer the string match gave
# before CE-2.20, which is the floor this fix must never go below.
COMMAND="echo 'gh workflow run ios-ci.yml' | bash"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
