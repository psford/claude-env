# Commit modifies BOTH a test file and an impl file. Mixed commits are
# out of scope for MVP — RED verification can't reason about them the
# same way. Hook MUST silently skip (no enforcement, no block).

setup_repo() {
  mkdir -p src
  echo "baseline" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  echo "new impl" > src/app.ts
  cat > src/app.test.ts <<'TEST'
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('mixed commit', () => {
    expect(true).toBe(true)
  })
})
TEST
  git add src/app.ts src/app.test.ts
  git commit -q -m "feat(app): impl + test together (mixed)"
}
