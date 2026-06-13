# Test-only commit with FAIL_HERE marker + `RED: HEAD~1`. At the red sha
# (the parent), the test fails (shim sees marker, returns 1) — which is
# the proof the test catches its named bug. Hook exits 0.

setup_repo() {
  mkdir -p src
  echo "broken impl" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  mkdir -p src
  cat > src/app.test.ts <<'TEST'
// FAIL_HERE
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('catches the regression', () => {
    expect(true).toBe(false)
  })
})
TEST
  git add src/app.test.ts
  git commit -q -m "test(app): catch regression

RED: HEAD~1"
}
