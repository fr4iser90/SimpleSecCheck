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

- `test_multiple_repos.py` checks report access via `/api/results/{scan_id}/report` (session cookie).
- `test_queue_steps_sessions.py` requires **session auth** enabled to validate session isolation and report access.
