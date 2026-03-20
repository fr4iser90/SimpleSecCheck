# E2E Tests

These tests validate queue behavior, step logging, and session isolation.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
```

Ensure the stack is up (`docker compose up` from the repo root). For `test_scan_profiles_e2e.py`, the bootstrap target URL is **`tests/e2e/e2e_constants.E2E_API_BASE_URL`** (default `http://localhost:8080` — FastAPI backend, not only nginx on port 80). Bootstrap waits on **`GET /api/setup/health`** (works while setup is incomplete).

### `test_scan_profiles_e2e.py` — session bootstrap

Runs **once per pytest session** before tests:

- If setup is **not** complete: reads the setup token **only** from `docker compose logs backend` (last `Setup Token:` in the tail, same repo root / compose file as `E2E_COMPOSE_FILE` in `e2e_constants.py`); then verify + initialize with **auto-generated** admin email/password, `auth_mode: free`, `require_email_verification: false`, provisions the synthetic E2E user; credentials are kept in **`setup_bootstrap._bootstrap_state`** (not shell env vars).
- If setup **is** already complete: bootstrap **raises** — use a **fresh database**: from the repo root `docker compose down -v` then `docker compose up --build`, then re-run pytest.

See **`tests/e2e/README.md`** for details.

## Run all E2E tests

```bash
pytest tests/e2e -v -s
```

## Notes

- `test_multiple_repos.py` checks report access via `/api/results/{scan_id}/report` (session cookie).
- `test_queue_steps_sessions.py` requires **session auth** enabled to validate session isolation and report access.
- `test_worker_parallelism_benchmark.py` — 3× gleiches Git-Repo: nach jedem `max_concurrent_jobs`-Wechsel **automatisch** `docker compose restart worker` (Repo-Root/`SSC_COMPOSE_DIR`). Ohne Neustart nutzt der Worker die alte Slot-Zahl. `SSC_BENCHMARK_AUTO_RESTART=0` zum Abschalten. `MAX_CONCURRENT_JOBS` in Compose überschreibt die DB.
