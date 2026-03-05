# Development

SimpleSecCheck is a Docker-first project with an optional WebUI.

## WebUI (Dev)

```bash
docker compose --profile dev up --build
```

Then open **http://localhost:8080**.

### Local development (without Docker)

```bash
# Backend
cd scanner/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd webui/frontend
npm install
npm run dev
```

## CLI Scanner (Dev)

```bash
docker compose --profile dev run --rm scanner
```

## Notes

- The WebUI is a thin wrapper around the CLI scanner.
- No database and no persistent state (single-shot).
- Production mode has stricter limits; see the main README.
