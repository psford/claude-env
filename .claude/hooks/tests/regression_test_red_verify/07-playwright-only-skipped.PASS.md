# Commit modifies only Playwright spec files (.spec.ts). Playwright
# verification is out of scope for MVP (heavier — wrangler-dev spin-up
# per check). Hook MUST silently skip (logs but doesn't enforce).

setup_repo() {
  mkdir -p e2e
  echo "baseline" > README.md
  git add README.md
  git commit -q -m "baseline"

  cat > e2e/feed.spec.ts <<'SPEC'
import { test, expect } from '@playwright/test'
test('feed renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('article')).toBeVisible()
})
SPEC
  git add e2e/feed.spec.ts
  git commit -q -m "test(e2e): add feed playwright spec"
}
