# `gh -R owner/repo workflow run` -> the hard deny still fires.
#
# gh's global flags may precede the subcommand, so checking the fixed slot
# argv[1:3] is walked past by any `-R`. ci_cost_guard scans positionally for
# exactly this reason (CH-237.10 defect 1, where an -R dispatch reached an iOS
# repo the session was not sitting in); deploy_guard's copy checked the slot.
#
# One implementation answers this now, in _repo_context.gh_subcommand_at.
COMMAND="gh -R psford/road-trip workflow run ios-ci.yml"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
