import { test as setup } from '@playwright/test'
import { seedDemoScans } from './seed-demo-data'
import { suppressCookieBanner } from './screenshot-helpers'

/** Seed demo scans for statistics/queue screenshots — runs AFTER active-scan audit. */
setup('seed demo scans for stats', async ({ page }) => {
  await suppressCookieBanner(page)
  await page.goto('/', { waitUntil: 'load' })
  await seedDemoScans(page)
})
