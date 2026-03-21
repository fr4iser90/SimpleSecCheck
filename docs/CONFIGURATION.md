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

## 6) SSE (global realtime, `/api/v1/events/stream`)

- **Auth:** The browser’s native `EventSource` **cannot** send an `Authorization: Bearer …` header. The UI relies on the **same-origin** request plus **`credentials: 'include'`** so the **`refresh_token` HttpOnly cookie** (or session) reaches the API. In-memory JWT alone is not enough for SSE unless you use a fetch-based stream polyfill.
- **Wire format:** All application messages use a single SSE event name **`ssc`**. Each `data:` line is one JSON object: **`{ "v": 1, "type": "…", "scope": "…", "payload": { … } }`**. Examples: `type: "system"` with `payload.kind` `connected` or `ping`; `type: "target_update"` / `scope: "targets"` (partial list hints); `type: "scan_update"` / `scope: "all"` with **`payload.list_revision`** matching **`GET /api/user/targets`** (plus `scan_id` / `status`) so clients can **skip** reloading the targets list when the revision is unchanged.
- **Keep-alive:** The stream emits periodic **system** envelopes (`payload.kind: "ping"`) so reverse proxies do not buffer or idle-timeout the connection. Behind **Nginx**, use `proxy_buffering off` and generous read timeouts for the SSE location.
- **Redis:** Workers can `PUBLISH` JSON on channel **`scan_events`**; the API forwards to the owning user’s SSE subscribers (includes `user_id` in the payload or resolves it from `scan_id`).

## 7) User targets list (`GET /api/user/targets`)

- **Shape:** **`{ "revision": "<hash>", "targets": [ … ] }` only** (not a bare array). The **`revision`** is a short SHA-256 fingerprint of the list (sorted by target id); **`ETag: W/"<revision>"`** is set on responses.
- **Caching:** Send **`If-None-Match: W/"<revision>"`** (or the raw revision) to receive **`304 Not Modified`** when nothing relevant changed.
