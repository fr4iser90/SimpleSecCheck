import type { Page } from '@playwright/test'

const base = () => process.env.BASE_URL || 'http://localhost'

/** Cancel pending/running jobs so the next audit scan starts immediately. */
export async function clearAuditQueue(page: Page): Promise<void> {
  for (const status of ['running', 'pending'] as const) {
    const res = await page.request.get(`${base()}/api/queue/?status=${status}&limit=100`)
    if (!res.ok()) continue
    const body = await res.json()
    for (const item of body.items ?? []) {
      const id = item.queue_id ?? item.scan_id
      if (!id) continue
      await page.request.delete(`${base()}/api/queue/${id}`)
    }
  }
  await page.waitForTimeout(800)
}
