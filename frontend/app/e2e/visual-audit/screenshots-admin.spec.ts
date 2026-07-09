import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from '@playwright/test'
import { preparePageForScreenshot, suppressCookieBanner } from './screenshot-helpers'

const OUT = join(dirname(fileURLToPath(import.meta.url)), 'output', 'admin')

const ADMIN_ROUTES: { path: string; name: string; waitMs?: number }[] = [
  { path: '/admin', name: 'dashboard' },
  { path: '/admin/users', name: 'users' },
  { path: '/admin/feature-flags', name: 'feature-flags' },
  { path: '/admin/auth', name: 'auth-settings' },
  { path: '/admin/execution', name: 'execution', waitMs: 1200 },
  { path: '/admin/queue', name: 'queue-settings' },
  { path: '/admin/scanner', name: 'scanner', waitMs: 1200 },
  { path: '/admin/tool-settings', name: 'tool-settings' },
  { path: '/admin/tool-duration', name: 'tool-duration' },
  { path: '/admin/policies', name: 'policies' },
  { path: '/admin/vulnerabilities', name: 'vulnerabilities' },
  { path: '/admin/scan-policies', name: 'scan-policies' },
  { path: '/admin/notifications', name: 'notifications' },
  { path: '/admin/settings', name: 'system-settings' },
  { path: '/admin/legal', name: 'legal' },
  { path: '/admin/health', name: 'health', waitMs: 1000 },
  { path: '/admin/audit-log', name: 'audit-log' },
  { path: '/admin/security/ip-control', name: 'ip-control' },
  { path: '/admin/sse-debug', name: 'sse-debug', waitMs: 1500 },
  { path: '/profile', name: 'profile' },
  { path: '/api-keys', name: 'api-keys' },
  { path: '/my-scans', name: 'my-scans', waitMs: 1200 },
  { path: '/my-targets', name: 'my-targets' },
]

const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const route of ADMIN_ROUTES) {
  for (const vp of VIEWPORTS) {
    test(`${route.name} @ ${vp.name}`, async ({ page }) => {
      await suppressCookieBanner(page)
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto(route.path, { waitUntil: 'load' })
      await preparePageForScreenshot(page, route.waitMs ?? 600)

      const dir = join(OUT, route.name)
      mkdirSync(dir, { recursive: true })
      await page.screenshot({
        path: join(dir, `${vp.name}.png`),
        fullPage: true,
      })
    })
  }
}
