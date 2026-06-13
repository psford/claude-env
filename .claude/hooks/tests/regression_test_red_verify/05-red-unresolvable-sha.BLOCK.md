# Test-only commit with `RED: <bogus-sha>` that doesn't resolve. Hook
# MUST block — can't verify against a sha that doesn't exist.

setup_repo() {
  mkdir -p src
  echo "baseline" > src/app.ts
  git add src/app.ts
  git commit -q -m "impl baseline"

  cat > src/app.test.ts <<'TEST'
// FAIL_HERE
import { describe, it, expect } from 'vitest'
describe('app', () => {
  it('claims a sha that does not exist', () => {
    expect(true).toBe(false)
  })
})
TEST
  git add src/app.test.ts
  git commit -q -m "test(app): bad sha

RED: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
}
