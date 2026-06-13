# Test-only commit with `RED: none` (explicit greenfield opt-out). No
# red sha to verify against. Hook MUST pass through silently.

setup_repo() {
  mkdir -p src
  echo "baseline" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  cat > src/app.test.ts <<'TEST'
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('is a brand-new feature with no broken-state history', () => {
    expect(true).toBe(true)
  })
})
TEST
  git add src/app.test.ts
  git commit -q -m "test(app): greenfield, no broken state in history

RED: none"
}
