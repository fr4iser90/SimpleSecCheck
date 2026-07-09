import { readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const TOKEN_FILE = join(dirname(fileURLToPath(import.meta.url)), '.setup-token')
const LEGACY_TOKEN_FILE = join(dirname(fileURLToPath(import.meta.url)), '..', '.auth', 'setup-token.txt')

/** Setup token from env (set by run-visual-audit.sh) or e2e/.auth/setup-token.txt */
export function resolveSetupToken(): string {
  const fromEnv = process.env.SETUP_TOKEN?.trim()
  if (fromEnv) return fromEnv.toLowerCase()

  if (existsSync(TOKEN_FILE)) {
    const fromFile = readFileSync(TOKEN_FILE, 'utf8').trim()
    if (fromFile) return fromFile.toLowerCase()
  }

  if (existsSync(LEGACY_TOKEN_FILE)) {
    const fromFile = readFileSync(LEGACY_TOKEN_FILE, 'utf8').trim()
    if (fromFile) return fromFile.toLowerCase()
  }

  throw new Error(
    'SETUP_TOKEN not set. Run scripts/run-visual-audit.sh from the repo root after docker compose up.',
  )
}
