# The REST spelling of the same thing. The CLI subcommand was covered; a guard
# that only knew one spelling would be walked around by typing the other.
COMMAND="gh api -X POST repos/owner/repo/actions/workflows/12/dispatches"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
