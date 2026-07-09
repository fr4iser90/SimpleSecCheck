#!/usr/bin/env bash
# Full visual audit: fresh stack → setup wizard screenshots → public + admin pages.
# Usage (from repo root):
#   ./scripts/run-visual-audit.sh
#   ./scripts/run-visual-audit.sh --reset   # docker compose down -v first
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.61.1-jammy}"
APP_DIR="$ROOT/frontend/app"
AUTH_DIR="$APP_DIR/e2e/.auth"
AUDIT_DIR="$APP_DIR/e2e/visual-audit"
TOKEN_FILE="$AUDIT_DIR/.setup-token"
mkdir -p "$AUTH_DIR" "$AUDIT_DIR/output" 2>/dev/null || true
# .auth may be root-owned from prior docker runs — recreate as current user
if [[ -d "$AUTH_DIR" ]] && [[ ! -w "$AUTH_DIR" ]]; then
  docker run --rm -v "$APP_DIR:/work" -u "$(id -u):$(id -g)" alpine sh -c 'rm -rf /work/e2e/.auth && mkdir -p /work/e2e/.auth' 2>/dev/null || true
fi
mkdir -p "$AUTH_DIR"

if [[ "${1:-}" == "--reset" ]]; then
  echo "==> Resetting volumes (docker compose down -v)…"
  docker compose down -v
fi

echo "==> Starting stack…"
docker compose up -d --build

echo "==> Waiting for backend health…"
for _ in $(seq 1 90); do
  if curl -sf "http://localhost:8080/api/setup/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

STATUS_JSON="$(curl -sf "http://localhost:8080/api/setup/status" || echo '{}')"
if echo "$STATUS_JSON" | grep -q '"setup_complete":false'; then
  echo "==> Fresh install — extracting setup token from backend logs…"
  sleep 5
  TOKEN="$(docker compose logs backend 2>&1 | grep -oE 'Setup Token: [a-f0-9]{64}' | tail -1 | awk '{print $3}' || true)"
  if [[ -z "${TOKEN:-}" ]]; then
    echo "ERROR: Could not find Setup Token in backend logs." >&2
    exit 1
  fi
  echo "$TOKEN" >"$TOKEN_FILE"
  export SETUP_TOKEN="$TOKEN"
  echo "    Token written to e2e/visual-audit/.setup-token"
else
  echo "==> Setup already complete — wizard screenshots will be skipped."
  rm -f "$TOKEN_FILE"
fi

export E2E_ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@example.com}"
export E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-VisualAudit123!}"
export E2E_ADMIN_USERNAME="${E2E_ADMIN_USERNAME:-admin}"
export BASE_URL="${BASE_URL:-http://localhost}"
export E2E_API_BASE_URL="${E2E_API_BASE_URL:-http://localhost:8080}"

echo "==> Running Playwright visual audit (wizard → public → admin)…"
docker run --rm -v "$APP_DIR:/work" alpine sh -c 'rm -rf /work/test-results /work/playwright-report' 2>/dev/null || true
docker run --rm --network host \
  -u "$(id -u):$(id -g)" \
  -v "$APP_DIR:/work" -w /work \
  -e BASE_URL -e E2E_API_BASE_URL -e SETUP_TOKEN \
  -e E2E_ADMIN_EMAIL -e E2E_ADMIN_PASSWORD -e E2E_ADMIN_USERNAME \
  "$PLAYWRIGHT_IMAGE" \
  npx --yes @playwright/test@1.61.1 test -c playwright.config.ts

echo "==> Done. Screenshots: frontend/app/e2e/visual-audit/output/"
echo "    Admin login: $E2E_ADMIN_EMAIL / $E2E_ADMIN_PASSWORD"
