import type { Page } from '@playwright/test'

const DEMO_TARGETS = [
  'https://github.com/octocat/Hello-World',
  'https://github.com/github/gitignore',
]

async function waitForScanners(page: Page, base: string): Promise<string[]> {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const scannersRes = await page.request.get(`${base}/api/scanners/?scan_type=code`)
    if (scannersRes.ok()) {
      const body = await scannersRes.json()
      const names = (body.scanners ?? [])
        .filter((s: { enabled?: boolean; name?: string }) => s.enabled && s.name)
        .slice(0, 2)
        .map((s: { name: string }) => s.name)
      if (names.length > 0) return names
    }
    await page.waitForTimeout(5000)
  }
  return []
}

/** Queue a few scans so queue/statistics screenshots are not empty. */
export async function seedDemoScans(page: Page): Promise<void> {
  const base = process.env.BASE_URL || 'http://localhost'
  try {
    const scanners = await waitForScanners(page, base)

    for (let i = 0; i < DEMO_TARGETS.length; i += 1) {
      const res = await page.request.post(`${base}/api/v1/scans/`, {
        data: {
          name: `Visual audit demo ${i + 1}`,
          description: 'Seeded for screenshot audit',
          scan_type: 'code',
          target_url: DEMO_TARGETS[i],
          scanners,
          tags: ['visual-audit'],
        },
      })
      if (!res.ok()) break
    }
  } catch {
    /* non-fatal — empty stats are acceptable */
  }
}
