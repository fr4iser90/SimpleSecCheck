# End-to-end tests (scan profiles, Checkov, …)

## Fresh database (required)

These tests run the **setup wizard** when `GET /api/setup/status` reports setup incomplete. If the app was **already** initialized (existing Postgres volume), bootstrap **fails** on purpose.

**Reset volumes and start clean** from the repository root:

```bash
docker compose down -v
docker compose up --build
```

Then run pytest (with the stack still up).

## Configuration (no `SSC_E2E_*` env vars)

- API base URL: `tests/e2e/e2e_constants.py` → `E2E_API_BASE_URL` (default `http://localhost:8080` — FastAPI backend, not nginx alone).
- Compose file name for `docker compose logs backend`: `E2E_COMPOSE_FILE` (default `docker-compose.yml`).
- Scan wait / httpx timeouts: **`tests/e2e/manifest_timeouts.py`** reads `scan_profiles.*.timeout` from `scanner/plugins/*/manifest.yaml`.

Credentials after bootstrap live in **`setup_bootstrap._bootstrap_state`** (in-process), not in shell environment variables.
