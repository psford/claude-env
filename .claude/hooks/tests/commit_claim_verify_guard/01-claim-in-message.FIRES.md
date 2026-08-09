# A commit message asserting "verified" must draw the verification demand.
COMMAND='git commit -m "fix(CH-1): verified against the live endpoint"'
EXPECT_MATCH='COMMIT-CLAIM VERIFICATION REQUIRED'
