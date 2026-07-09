/**
 * Running-scan screenshots. Queue is cleared first; one quick scan is started via API.
 */
import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'
import { openRunningScanView, startActiveAuditScan } from './active-scan-helpers'
import { clearAuditQueue } from './queue-cleanup'
import { preparePageForScreenshot, suppressCookieBanner } from './screenshot-helpers'

const OUT = join(dirname(fileURLToPath(import.meta.url)), 'output', 'active-scan')

test.describe.configure({ timeout: 120_000 })

test.describe('Active scan visual audit', () => {
  test('running scan screenshots', async ({ page }) => {
    await suppressCookieBanner(page)
    await clearAuditQueue(page)

    const scanId = await startActiveAuditScan(page)
    await openRunningScanView(page, scanId)
    await expect(page.getByRole('heading', { name: 'Waiting in Queue' })).toHaveCount(0)

    const shot = async (subdir: string, name: string, w: number, h: number) => {
      await page.setViewportSize({ width: w, height: h })
      mkdirSync(join(OUT, subdir), { recursive: true })
      await preparePageForScreenshot(page, 300)
      await page.screenshot({ path: join(OUT, subdir, name), fullPage: true })
    }

    await shot('scan-progress', 'desktop.png', 1280, 800)
    await shot('scan-progress', 'mobile.png', 390, 844)

    await page.getByTitle('View Steps').click()
    await page.getByRole('heading', { name: /Scan Steps/i }).waitFor({ state: 'visible', timeout: 10_000 })
    await shot('steps-sidebar', 'desktop.png', 1280, 800)
  })
})
