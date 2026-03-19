# Configuration

SimpleSecCheck has three layers of settings: **environment variables** (`.env` / compose), **database-backed config** (after Setup), and **Admin UI** (runtime overrides).

## 1) Environment (Docker / `.env`)

- **Compose** loads `backend` and `worker` from `.env` (`env_file` in `docker-compose.yml`). Copy values from your deployment secrets; required keys include at least **`POSTGRES_PASSWORD`**, **`SECRET_KEY`**, **`JWT_SECRET_KEY`**, **`SESSION_SECRET`** (see backend startup logs if something is missing).
- **Inline reference** at the bottom of `docker-compose.yml` lists common variables (Postgres, Redis, `API_BASE_URL`, scanner resource limits, etc.).

## 2) Backend application settings

The authoritative list of **env-backed** settings is **[`backend/config/settings.py`](../backend/config/settings.py)** (Pydantic `Field(..., description=...)`). Examples:

| Area | Examples |
|------|----------|
| Database / cache | `POSTGRES_*`, `REDIS_URL`, pool sizes |
| Auth | `AUTH_MODE`, `ACCESS_MODE`, JWT/session secrets, registration flags |
| Scan policy (defaults) | `ALLOW_GIT_REPOS`, `ALLOW_WEBSITE_SCANS`, `ALLOW_LOCAL_PATHS`, ZIP limits, queue priorities |
| Email | `SMTP_*`, verification / password-reset TTLs |
| Integrations | `GITHUB_TOKEN`, `NVD_API_KEY` (often also passed to scanner), `DOCKER_*` |

After **Setup**, many values can be overridden from **PostgreSQL** (`load_settings_from_database` in the same file)—the Admin UI edits the same logical config.

## 3) Admin UI (runtime)

For a running stack: **Admin** pages (execution, queue, security policies, scanner registry, feature flags, auth, etc.) adjust behaviour without redeploying. See [CHANGELOG](../CHANGELOG.md) release notes for the 2.1.x Admin surface.

## 4) Scanner-only / CLI

Scanner containers are driven by **environment variables** (e.g. `SCAN_TYPE`, `TARGET_TYPE`, `SCAN_TARGET`, `COLLECT_METADATA`). Full tables and examples: **[CLI_DOCKER.md](CLI_DOCKER.md)** and **`python3 -m scanner.core.help`** inside the scanner image.

## 5) Frontend

Build-time and nginx behaviour: **[`frontend/README.md`](../frontend/README.md)** (`API_BASE_URL`, asset build).
