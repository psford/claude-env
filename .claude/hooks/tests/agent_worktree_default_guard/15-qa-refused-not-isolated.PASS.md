{
  "tool_name": "Agent",
  "session_id": "test-session",
  "tool_input": {
    "subagent_type": "psford-tickets:qa",
    "description": "CE-2.44: qa is refused, not isolated",
    "prompt": "This fixture used to pin qa as still forced into worktree isolation (CE-2.15, fixture 11's companion). CE-2.44 refuses the dispatch outright instead: Claude Code, not this hook, picks the commit an Agent-tool worktree starts from, so forcing isolation on a role that judges a commit would let it silently review whichever commit worktree happened to start from. This driver can only tell an injected isolation from silence, not a refusal, so it reads the denial as PASS -- isolation is not forced. The actual assertion that the dispatch is denied, and that the denial names glm-agent, lives in tests/test_agent_worktree_default_guard.py::TestAReviewerDispatch."
  }
}
