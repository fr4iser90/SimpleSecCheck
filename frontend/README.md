# SimpleSecCheck WebUI

Optional web interface for SimpleSecCheck. **Frontend-only** (nginx) that proxies API calls to the internal worker.

## Features

- ✅ Start scans via web interface
- ✅ Docker image scans (Anchore)
- ✅ Live progress and logs during scan
- ✅ View HTML reports after scan
- ✅ Browse local results (file browser)
- ❌ No dashboard/history (single-shot principle)
- ❌ No persistent infrastructure

## Usage

### Start WebUI (Optional)

```bash
# Start WebUI + worker in dev
docker compose --profile dev up --build

# Access at http://localhost:8080
```

The WebUI container is nginx only; the worker container runs the backend+scanner.

### Development

```bash
# Frontend (separate terminal)
cd frontend/frontend
npm install
npm run dev
```

## Architecture

- **WebUI**: nginx serving static frontend; `/api/*` is proxied to worker
- **Worker**: FastAPI + Scanner (queue + scan execution)

## API Endpoints

- `POST /api/scan/start` - Start scan
- `GET /api/scan/status` - Get scan status
- `GET /api/scan/logs` - Stream logs (SSE)
- `GET /api/scan/report` - Get HTML report
- `GET /api/results` - List all results

## Notes

- WebUI is **completely optional** - CLI still works as before
- WebUI follows single-shot principle - no persistent state
- All scans are independent - no history tracking
- Production mode: Docker image scans only accept Docker Hub images (docker.io/... or unqualified)
