#!/usr/bin/env bash
# Verify that the RUNNING frontend container serves the bundle built from the CURRENT checkout.
#
# Why: a `docker compose up -d --build` can report success while BuildKit reuses an old
# "COPY --from=build /app/dist" layer, leaving the container serving a stale bundle.
# Success here means: asset set in the container == asset set a clean build of this tree produces.
#
# Usage (from anywhere):
#   ./scripts/verify-frontend-deploy.sh
#   CONTAINER=SimpleSecCheck_frontend ./scripts/verify-frontend-deploy.sh
#   ./scripts/verify-frontend-deploy.sh --container ssc-fe-test
#
# Exit codes: 0 = deployed bundle matches; 1 = mismatch or failed precondition.
# Needs: docker, network (npm ci inside the expected-build container).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/frontend/app"
DOCKERFILE="$ROOT/frontend/Dockerfile.nginx"
HTML_ASSETS_DIR="/usr/share/nginx/html/assets"
CONTAINER="${CONTAINER:-SimpleSecCheck_frontend}"
DOCKER="${DOCKER:-docker}"
LOCK_PACKAGES=(browserslist nanoid postcss source-map-js vite react-router-dom)

fail() { echo "FAIL: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container) CONTAINER="${2:?--container needs a name}"; shift 2 ;;
    -h|--help) sed -n '/^set /q; s/^#[[:space:]]\{0,1\}//p' "$0"; exit 0 ;;
    *) fail "unknown argument: $1 (see --help)" ;;
  esac
done

command -v "$DOCKER" >/dev/null 2>&1 || fail "docker not available (\$DOCKER=$DOCKER)"
[[ -f "$DOCKERFILE" ]] || fail "missing $DOCKERFILE"
[[ -f "$APP_DIR/package-lock.json" ]] || fail "missing $APP_DIR/package-lock.json"

BASE_IMAGE="$(awk '/^FROM node:/ {print $2; exit}' "$DOCKERFILE")"
[[ -n "$BASE_IMAGE" ]] || fail "no 'FROM node:...' base image found in $DOCKERFILE"

echo "== context =="
echo "checkout:      $(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo 'not a git checkout')"
DIRTY="$(git -C "$ROOT" status --porcelain -- frontend/app 2>/dev/null || true)"
if [[ -n "$DIRTY" ]]; then
  echo "frontend/app:  DIRTY (built expectation follows the working tree, not HEAD)"
else
  echo "frontend/app:  clean"
fi
if command -v python3 >/dev/null 2>&1; then
  python3 - "$APP_DIR/package-lock.json" "${LOCK_PACKAGES[@]}" <<'PY'
import json, sys
lock, pkgs = sys.argv[1], sys.argv[2:]
data = json.load(open(lock)).get("packages", {})
print("lockfile:      " + "  ".join(
    f"{p}={data.get('node_modules/' + p, {}).get('version', 'absent')}" for p in pkgs))
PY
fi
echo "container:     $CONTAINER"
echo "build base:    $BASE_IMAGE"

[[ "$("$DOCKER" inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo false)" == "true" ]] \
  || fail "container '$CONTAINER' is not running"

echo
echo "== served by container =="
SERVED="$("$DOCKER" exec "$CONTAINER" sh -c "cd '$HTML_ASSETS_DIR' && ls -1 | sort" 2>/dev/null)" \
  || fail "cannot read $HTML_ASSETS_DIR from '$CONTAINER' (wrong container name or not an nginx frontend image)"
[[ -n "$SERVED" ]] || fail "$HTML_ASSETS_DIR is empty in '$CONTAINER'"
"$DOCKER" exec "$CONTAINER" sh -c "ls -l '$HTML_ASSETS_DIR'" | sed 's/^/  /'

echo
echo "== expected from this checkout (clean build in $BASE_IMAGE) =="
EXPECTED="$("$DOCKER" run --rm -v "$APP_DIR:/src:ro" -w /work "$BASE_IMAGE" sh -c '
  set -e
  tar -C /src --exclude=node_modules --exclude=dist -cf - . | tar -C /work -xf -
  npm ci --no-audit --no-fund >/dev/null 2>&1
  npm run build >/dev/null 2>&1
  cd /work/dist/assets && ls -l
')" || fail "expected-build container failed (npm ci / tsc / vite build)"
EXPECTED_NAMES="$(printf '%s\n' "$EXPECTED" | awk 'NF>=9 {print $NF}' | grep -E '^index-.*\.(js|css)$' | sort)"
[[ -n "$EXPECTED_NAMES" ]] || fail "expected build produced no index-*.js/css assets"
printf '%s\n' "$EXPECTED" | sed 's/^/  /'

echo
echo "== comparison =="
if [[ "$SERVED" == "$EXPECTED_NAMES" ]]; then
  echo "OK: deployed assets match a clean build of this checkout"
  exit 0
fi

echo "MISMATCH: deployed assets differ from a clean build of this checkout" >&2
diff --label "served (running container)" <(printf '%s\n' "$SERVED") \
     --label "expected (clean build)" <(printf '%s\n' "$EXPECTED_NAMES") >&2 || true
cat >&2 <<EOF

Causes to rule out, in this order:
1) Running container is not the newest image:
     docker compose -f compose.traefik.yaml up -d --force-recreate frontend
2) The build picked up leftovers from the checkout instead of npm ci.
   .dockerignore must exclude nested dirs, not just the context root:
     grep -n 'node_modules' .dockerignore     # want: **/node_modules
   (A plain "node_modules" leaves frontend/app/node_modules in the build context,
    and "COPY frontend/app/ ./" then overwrites the npm ci result with it.)
3) The checkout itself lacks the upgrade: compare the checkout/lockfile lines
   above against origin/main on that host.

Then rebuild without cache and re-run this script:
  docker compose -f compose.traefik.yaml build --no-cache frontend
  docker compose -f compose.traefik.yaml up -d --force-recreate frontend
  ./scripts/verify-frontend-deploy.sh
EOF
exit 1
