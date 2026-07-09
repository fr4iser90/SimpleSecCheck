# Visual UI audit (screenshots)

Desktop + mobile screenshots for gap analysis — including **setup wizard**, public routes, and admin pages.

## One command (recommended)

From the **repository root** after a DB reset:

```bash
chmod +x scripts/run-visual-audit.sh
./scripts/run-visual-audit.sh --reset
```

Or without volume reset (wizard screenshots skip if setup is already complete):

```bash
./scripts/run-visual-audit.sh
```

This script:

1. Starts `docker compose up -d --build`
2. Reads the setup token from backend logs (fresh DB only)
3. Runs Playwright: **wizard → login → public → admin**

## Fixed test credentials (visual audit only)

| Field | Value |
|-------|--------|
| Email | `admin@example.com` |
| Password | `VisualAudit123!` |
| Username | `admin` |

Created automatically by the setup wizard flow. Saved to `e2e/.auth/credentials.json` (gitignored).

## Output folders

| Folder | Content |
|--------|---------|
| `output/setup-wizard/` | Steps 0–4 (token, use case, admin, config, legal) |
| `output/<route>/` | Public pages (home, queue, legal, …) |
| `output/admin/<route>/` | Admin + authenticated pages |

## Manual Playwright (frontend/app)

```bash
export BASE_URL=http://localhost
export E2E_API_BASE_URL=http://localhost:8080
export SETUP_TOKEN=<from docker compose logs backend>
export E2E_ADMIN_EMAIL=admin@example.com
export E2E_ADMIN_PASSWORD='VisualAudit123!'

npm run screenshots:all
```

## Projects (playwright.config.ts)

| Project | Spec | Depends on |
|---------|------|------------|
| `wizard` | `screenshots-setup-wizard.spec.ts` | — |
| `auth` | `auth.setup.ts` | wizard |
| `public` | `screenshots.spec.ts` | wizard |
| `admin` | `screenshots-admin.spec.ts` | auth |

Wizard tests **skip** when `setup_complete` is already true — use `docker compose down -v` for wizard screenshots.

## Tips

- Dismiss cookie banner manually in screenshots if it overlaps — wizard enables legal + cookie notice by default.
- Compare `output/` across branches after UI changes.
- Python E2E (`tests/e2e/setup_bootstrap.py`) uses random admin creds; visual audit uses **fixed** creds above.
