import type { Page } from '@playwright/test'

export const ACTIVE_SCAN_TARGET = 'https://github.com/fr4iser90/SimpleSecCheck'

const base = () => process.env.BASE_URL || 'http://localhost'

export async function waitForScanProgressUi(page: Page, timeoutMs = 90_000): Promise<void> {
  await page.getByRole('heading', { name: 'Scan in Progress...' }).waitFor({
    state: 'visible',
    timeout: timeoutMs,
  })
  await page.locator('.scan-step-card').first().waitFor({
    state: 'visible',
    timeout: timeoutMs,
  })
}

/** Start one quick scan via API (after queue cleanup). Returns scan id. */
export async function startActiveAuditScan(page: Page): Promise<string> {
  const scannersRes = await page.request.get(`${base()}/api/scanners/?scan_type=code`)
  if (!scannersRes.ok()) throw new Error('Failed to load scanners')
  const body = await scannersRes.json()
  const scanners = (body.scanners ?? [])
    .filter((s: { enabled?: boolean; name?: string }) => s.enabled && s.name)
    .slice(0, 4)
    .map((s: { name: string }) => s.name)
  if (scanners.length === 0) throw new Error('No scanners available')

  const res = await page.request.post(`${base()}/api/v1/scans/`, {
    data: {
      name: 'Visual audit active scan',
      description: 'Active-scan screenshot audit',
      scan_type: 'code',
      target_url: ACTIVE_SCAN_TARGET,
      scanners,
      config: { scan_profile: 'quick' },
      tags: ['visual-audit-active'],
    },
  })
  if (!res.ok()) {
    throw new Error(`Failed to start scan: ${res.status()} ${await res.text()}`)
  }
  const scan = await res.json()
  return scan.id as string
}

export async function openRunningScanView(page: Page, scanId: string): Promise<void> {
  const deadline = Date.now() + 90_000
  while (Date.now() < deadline) {
    const res = await page.request.get(`${base()}/api/queue/${scanId}/status`)
    if (res.ok()) {
      const status = await res.json()
      if (status.status === 'running') break
    }
    await page.waitForTimeout(2000)
  }

  await page.goto('/my-scans', { waitUntil: 'load' })
  const card = page.locator('.mobile-data-card, tr').filter({ hasText: /SimpleSecCheck/i }).first()
  await card.getByRole('button', { name: /View steps/i }).click()
  await page.waitForURL('**/scan', { timeout: 20_000 })
  await waitForScanProgressUi(page)
}
