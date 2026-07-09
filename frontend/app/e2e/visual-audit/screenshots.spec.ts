/**
 * Visual audit: desktop + mobile screenshots of public routes.
 *
 * Usage:
 *   cd frontend/app
 *   npm install
 *   npx playwright install chromium
 *   BASE_URL=http://localhost npm run screenshots:audit
 *
 * Output: e2e/visual-audit/output/<route>/<viewport>.png
 *
 * Admin/auth routes need a saved session — see README.md in this folder.
 */
import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from '@playwright/test'
import { preparePageForScreenshot, suppressCookieBanner } from './screenshot-helpers'

const OUT = join(dirname(fileURLToPath(import.meta.url)), 'output')

const PUBLIC_ROUTES: { path: string; name: string; waitMs?: number }[] = [
  { path: '/', name: 'home' },
  { path: '/scan', name: 'scan' },
  { path: '/queue', name: 'queue', waitMs: 1500 },
  { path: '/statistics', name: 'statistics', waitMs: 3500 },
  { path: '/capabilities', name: 'capabilities' },
  { path: '/login', name: 'login' },
  { path: '/signup', name: 'signup' },
  { path: '/legal/impressum', name: 'legal-impressum' },
  { path: '/legal/privacy', name: 'legal-privacy' },
  { path: '/legal/terms', name: 'legal-terms' },
]

const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const route of PUBLIC_ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`${route.name} @ ${vp.name}`, async ({ page }) => {
      await suppressCookieBanner(page)
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto(`${process.env.BASE_URL || 'http://localhost'}${route.path}`, { waitUntil: 'load' })
      if (route.name === 'home') {
        const target = page.locator('#target')
        await target.waitFor({ state: 'visible', timeout: 10_000 })
        await target.click()
        await target.fill('https://github.com/octocat/Hello-World')
        await target.blur()
        await page.waitForResponse(
          (r) => r.url().includes('/api/v1/scans/detect-scan-type') && r.ok(),
          { timeout: 15_000 },
        ).catch(() => null)
        await page.waitForResponse(
          (r) => r.url().includes('/api/scanners/') && r.ok(),
          { timeout: 15_000 },
        ).catch(() => null)
        await page.waitForTimeout(600)
      }
      if (route.name === 'statistics') {
        await page.waitForResponse(
          (r) => r.url().includes('/api/v1/scans/statistics') && r.ok(),
          { timeout: 15000 },
        )
        await preparePageForScreenshot(page, 400)
      } else {
        await preparePageForScreenshot(page, route.waitMs ?? 600)
      }
      const dir = join(OUT, route.name)
      mkdirSync(dir, { recursive: true })
      await page.screenshot({
        path: join(dir, `${vp.name}.png`),
        fullPage: true,
      })
    })
  }
}
