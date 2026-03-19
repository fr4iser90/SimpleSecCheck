# Alembic – Schema versioning

Schema is **only** updated via Alembic. No `create_all`, no `_ensure_*` for schema.

- **pgcrypto**: Used for `gen_random_uuid()` on primary keys (enable once per DB).
- **updated_at**: Parametrized trigger function: optional TG_ARGV = column names to exclude from “changed” check (e.g. JSONB). Column-based triggers on `scans` and `user_scan_targets` (UPDATE OF …) to reduce write overhead; only “meaningful” columns fire.
- **ENUMs**: `user_role_enum`, `scan_status_enum`, `severity_enum` enforce allowed values at DB level.
- **system_state**: Singleton row; only row allowed has `id = 00000000-0000-0000-0000-000000000001` (see `SYSTEM_STATE_SINGLETON_ID` in models).

## Run migrations

From **backend** directory (or with `PYTHONPATH=backend`):

```bash
alembic upgrade head
```

At app startup this runs automatically via `infrastructure.database.alembic_runner.run_alembic_upgrade()`.

## Create a new revision (schema change)

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "add field xyz"
# Review the generated migration, then:
alembic upgrade head
```

## Clean slate (reset DB)

1. Drop the database (or `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`).
2. Run `alembic upgrade head` (or start the app).

`001_initial_schema.py` creates all tables; no `IF NOT EXISTS` – Alembic manages state.

- **scans.results**: Full GIN on `results` plus partial GIN `idx_scans_results_completed` (WHERE status = 'completed' AND results IS NOT NULL) for heavy completed-scan queries. For very large query patterns, a materialized view can be added later.
