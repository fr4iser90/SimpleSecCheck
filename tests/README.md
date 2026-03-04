# E2E Tests

These tests validate queue behavior, step logging, and session isolation.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
```

Ensure the WebUI backend is running on `http://localhost:8080`.

## Run all E2E tests

```bash
pytest tests/e2e -v -s
```

## Notes

- `test_multiple_repos.py` runs in dev or prod. In production it validates report access via `/api/my-results/{scan_id}/report`.
- `test_queue_steps_sessions.py` requires **production mode** with sessions enabled to validate session isolation and report access.
