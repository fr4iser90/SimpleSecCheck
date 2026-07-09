import { defineConfig } from '@playwright/test'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const AUTH_FILE = join(dirname(fileURLToPath(import.meta.url)), 'e2e', '.auth', 'admin.json')

export default defineConfig({
  testDir: './e2e/visual-audit',
  timeout: 120_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost',
    screenshot: 'off',
    trace: 'off',
  },
  projects: [
    {
      name: 'wizard',
      testMatch: /screenshots-setup-wizard\.spec\.ts/,
    },
    {
      name: 'auth',
      testMatch: /auth\.setup\.ts/,
      dependencies: ['wizard'],
    },
    {
      name: 'active-scan',
      testMatch: /screenshots-active-scan\.spec\.ts/,
      dependencies: ['auth'],
      timeout: 120_000,
      use: { storageState: AUTH_FILE },
    },
    {
      name: 'seed',
      testMatch: /seed\.setup\.ts/,
      dependencies: ['active-scan'],
      use: { storageState: AUTH_FILE },
    },
    {
      name: 'public',
      testMatch: /screenshots\.spec\.ts/,
      dependencies: ['wizard', 'auth', 'seed'],
    },
    {
      name: 'admin',
      testMatch: /screenshots-admin\.spec\.ts/,
      dependencies: ['auth', 'seed'],
      use: { storageState: AUTH_FILE },
    },
  ],
})
