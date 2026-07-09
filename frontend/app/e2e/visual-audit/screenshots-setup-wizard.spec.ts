/**
 * Setup wizard UI screenshots + completes first-run setup with fixed audit credentials.
 * Requires a fresh database (setup_complete=false). Skips when setup is already done.
 */
import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'
import {
  AUDIT_ADMIN_EMAIL,
  AUDIT_ADMIN_PASSWORD,
  AUDIT_ADMIN_USERNAME,
  AUDIT_LEGAL,
} from './audit-credentials'
import { saveAuditCredentials } from './credentials-store'
import { resolveSetupToken } from './setup-token'
import { dismissCookieBanner } from './screenshot-helpers'

const OUT = join(dirname(fileURLToPath(import.meta.url)), 'output', 'setup-wizard')
const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:8080'

const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
] as const

async function setupIncomplete(request: import('@playwright/test').APIRequestContext): Promise<boolean> {
  const res = await request.get(`${API_BASE}/api/setup/status`)
  if (!res.ok()) return false
  const data = await res.json()
  return !data.setup_complete
}

async function screenshotStep(
  page: import('@playwright/test').Page,
  stepName: string,
) {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height })
    const dir = join(OUT, stepName)
    mkdirSync(dir, { recursive: true })
    await page.waitForTimeout(300)
    await page.screenshot({ path: join(dir, `${vp.name}.png`), fullPage: true })
  }
}

test.describe.serial('Setup wizard visual audit', () => {
  let setupToken = ''

  test.beforeAll(async ({ request }) => {
    const incomplete = await setupIncomplete(request)
    if (!incomplete) {
      test.skip(true, 'Setup already complete — run: docker compose down -v && scripts/run-visual-audit.sh')
    }
    setupToken = resolveSetupToken()
    await new Promise((r) => setTimeout(r, 12_000))
  })

  test('walk wizard, screenshot all steps, complete setup', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/setup', { waitUntil: 'load' })
    await expect(page.getByRole('heading', { name: /Step 0: Verify Setup Token/i })).toBeVisible({
      timeout: 30_000,
    })
    await screenshotStep(page, 'step-0-token')

    await page.getByPlaceholder('Enter setup token').fill(setupToken)
    await page.getByRole('button', { name: /Verify Token/i }).click()
    await expect(page.getByRole('heading', { name: /Step 1: Select Deployment Use Case/i })).toBeVisible({
      timeout: 30_000,
    })
    await screenshotStep(page, 'step-1-use-case')

    await page.locator('.use-case-card').filter({ hasText: 'Public Web' }).first().click()
    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByRole('heading', { name: /Step 2: Create Admin User/i })).toBeVisible()
    await screenshotStep(page, 'step-2-admin-user')

    await page.locator('input[name="username"]').fill(AUDIT_ADMIN_USERNAME)
    await page.locator('input[name="email"]').fill(AUDIT_ADMIN_EMAIL)
    await page.locator('input[name="password"]').first().fill(AUDIT_ADMIN_PASSWORD)
    await page.locator('input[name="password_confirm"]').fill(AUDIT_ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Next' }).click()
    await expect(page.getByRole('heading', { name: /Step 3: System Configuration/i })).toBeVisible()
    await screenshotStep(page, 'step-3-configuration')

    await page.getByRole('button', { name: 'Next' }).click()
    await expect(page.getByRole('heading', { name: /Step 4: Legal/i })).toBeVisible({ timeout: 15_000 })
    await screenshotStep(page, 'step-4-legal-disabled')

    await page.locator('input[name="enabled"]').check()
    await page.locator('input[name="company_name"]').fill(AUDIT_LEGAL.company_name)
    await page.locator('input[name="legal_representative"]').fill(AUDIT_LEGAL.legal_representative)
    await page.locator('textarea[name="address"]').fill(AUDIT_LEGAL.address)
    await page.locator('input[name="email"]').last().fill(AUDIT_LEGAL.email)
    await page.locator('input[name="phone"]').fill(AUDIT_LEGAL.phone)
    await screenshotStep(page, 'step-4-legal-enabled')

    await page.getByRole('button', { name: /Complete Setup/i }).click()
    await page.waitForURL((url) => !url.pathname.includes('/setup'), { timeout: 90_000 })

    const dismiss = page.getByRole('button', { name: /Verstanden|Got it|Understood|OK|知道了/i })
    if (await dismiss.isVisible().catch(() => false)) {
      await dismiss.click()
    }

    saveAuditCredentials({
      admin_email: AUDIT_ADMIN_EMAIL,
      admin_password: AUDIT_ADMIN_PASSWORD,
      admin_username: AUDIT_ADMIN_USERNAME,
    })
  })
})
