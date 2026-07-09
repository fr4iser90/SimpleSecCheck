import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  AUDIT_ADMIN_EMAIL,
  AUDIT_ADMIN_PASSWORD,
  AUDIT_ADMIN_USERNAME,
} from './audit-credentials'

const AUTH_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '.auth')
const CREDENTIALS_FILE = join(AUTH_DIR, 'credentials.json')

export interface AuditCredentials {
  admin_email: string
  admin_password: string
  admin_username: string
}

export function auditCredentials(): AuditCredentials {
  const fromEnv =
    process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD
      ? {
          admin_email: process.env.E2E_ADMIN_EMAIL,
          admin_password: process.env.E2E_ADMIN_PASSWORD,
          admin_username: process.env.E2E_ADMIN_USERNAME || AUDIT_ADMIN_USERNAME,
        }
      : null

  if (fromEnv) return fromEnv

  if (existsSync(CREDENTIALS_FILE)) {
    const parsed = JSON.parse(readFileSync(CREDENTIALS_FILE, 'utf8')) as AuditCredentials
    if (parsed.admin_email && parsed.admin_password) return parsed
  }

  return {
    admin_email: AUDIT_ADMIN_EMAIL,
    admin_password: AUDIT_ADMIN_PASSWORD,
    admin_username: AUDIT_ADMIN_USERNAME,
  }
}

export function saveAuditCredentials(creds: AuditCredentials): void {
  mkdirSync(AUTH_DIR, { recursive: true })
  writeFileSync(CREDENTIALS_FILE, JSON.stringify(creds, null, 2) + '\n', 'utf8')
}
