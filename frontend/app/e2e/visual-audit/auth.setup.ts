import { test as setup } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { auditCredentials } from './credentials-store'
import { dismissCookieBanner, suppressCookieBanner } from './screenshot-helpers'

const AUTH_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '.auth')
const AUTH_FILE = join(AUTH_DIR, 'admin.json')

setup('authenticate as admin', async ({ page }) => {
  const { admin_email: email, admin_password: password } = auditCredentials()

  mkdirSync(AUTH_DIR, { recursive: true })

  const base = process.env.BASE_URL || 'http://localhost'
  await suppressCookieBanner(page)
  await page.goto(`${base}/login`, { waitUntil: 'load' })
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(password)
  await page.locator('button.login-button').click()

  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20_000 })
  await dismissCookieBanner(page)
  await page.context().storageState({ path: AUTH_FILE })
})
