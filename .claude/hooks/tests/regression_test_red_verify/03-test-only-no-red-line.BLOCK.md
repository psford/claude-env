# Test-only commit with NO `RED:` line at all. The convention requires
# every test-only commit to declare its RED sha (or `RED: none`). Hook
# MUST block.

setup_repo() {
  mkdir -p src
  echo "baseline" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  cat > src/app.test.ts <<'TEST'
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('asserts something', () => {
    expect(true).toBe(true)
  })
})
TEST
  git add src/app.test.ts
  git commit -q -m "test(app): add test with no RED line"
}
