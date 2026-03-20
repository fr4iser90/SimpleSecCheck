"""
Fixed E2E constants — scan wait/HTTP limits come from ``manifest_timeouts.py`` (manifests), not env vars.
"""
from __future__ import annotations

# FastAPI backend (not nginx :80 alone): bootstrap uses GET /api/setup/health.
E2E_API_BASE_URL = "http://localhost:8080"

# Compose file name at repo root (``docker compose -f … logs backend`` for setup token).
E2E_COMPOSE_FILE = "docker-compose.yml"

E2E_TEST_REPO_URL = "https://github.com/fr4iser90/SimpleSecCheck"

# Status polling loop only (not a scan timeout — those are manifest-derived in tests).
E2E_STATUS_POLL_INTERVAL_S = 5

# How long to wait for API / DB readiness during bootstrap.
E2E_BOOTSTRAP_WAIT_S = 300.0
