import type { Page } from '@playwright/test'

/** Prevent cookie banner from appearing on subsequent navigations. Call before goto(). */
export async function suppressCookieBanner(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      sessionStorage.setItem('ssc_cookie_notice_dismissed', '1')
    } catch {
      /* ignore */
    }
  })
}

/** Hide cookie banner so screenshots show page content. */
export async function dismissCookieBanner(page: Page): Promise<void> {
  const btn = page.getByRole('button', { name: /Verstanden|Got it|Understood|OK|知道了/i })
  if (await btn.isVisible().catch(() => false)) {
    await btn.click()
    await page.waitForTimeout(200)
  }
}

export async function preparePageForScreenshot(page: Page, waitMs = 500): Promise<void> {
  await dismissCookieBanner(page)
  await page.waitForTimeout(waitMs)
}
