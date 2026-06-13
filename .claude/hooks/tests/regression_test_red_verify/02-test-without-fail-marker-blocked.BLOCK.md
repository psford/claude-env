# Test-only commit with NO FAIL_HERE marker but claims `RED: HEAD~1`. At
# the red sha, the shim sees no marker and returns 0 (test "passes") —
# meaning the test does NOT catch what it claims. Hook MUST block.

setup_repo() {
  mkdir -p src
  echo "broken impl" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  cat > src/app.test.ts <<'TEST'
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('claims to catch the regression but does not', () => {
    expect(1).toBe(1)
  })
})
TEST
  git add src/app.test.ts
  git commit -q -m "test(app): shallow assertion

RED: HEAD~1"
}
