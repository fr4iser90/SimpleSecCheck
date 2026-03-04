# SimpleSecCheck WebUI

Optional web interface for SimpleSecCheck. **Single-shot principle**: No database, no state, just a CLI wrapper.

## Features

- ✅ Start scans via web interface
- ✅ Live progress and logs during scan
- ✅ View HTML reports after scan
- ✅ Browse local results (file browser)
- ❌ No dashboard/history (single-shot principle)
- ❌ No persistent infrastructure

## Usage

### Start WebUI (Optional)

```bash
# Start WebUI with docker-compose profile
docker-compose --profile webui up

# Access at http://localhost:8080
```

### Development

```bash
# Backend
cd webui/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend (separate terminal)
cd webui/frontend
npm install
npm run dev
```

## Architecture

- **Backend**: FastAPI - uses Python DockerRunner + orchestrator (no logic duplication)
- **Frontend**: React + TypeScript - minimal UI
- **No Database**: File system only
- **No State**: Each scan is independent

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
