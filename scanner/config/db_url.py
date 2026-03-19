"""Build PostgreSQL URL from POSTGRES_* env (no DATABASE_URL)."""

import os
from typing import Any, Dict, Optional
from urllib.parse import quote_plus


def asyncpg_connect_kwargs() -> Dict[str, Any]:
    """Match backend/worker POSTGRES_SSL: false = plain TCP inside Compose."""
    v = os.environ.get("POSTGRES_SSL", "false").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return {"ssl": True}
    return {"ssl": False}

REQUIRED_KEYS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
)


def database_url_from_postgres_env() -> Optional[str]:
    """Return asyncpg-compatible postgresql:// URL or None if any POSTGRES_* is missing."""
    if not all(os.getenv(k) for k in REQUIRED_KEYS):
        return None
    u = quote_plus(os.environ["POSTGRES_USER"])
    p = quote_plus(os.environ["POSTGRES_PASSWORD"])
    d = quote_plus(os.environ["POSTGRES_DB"])
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    return f"postgresql://{u}:{p}@{host}:{port}/{d}"


def require_database_url_from_postgres_env() -> str:
    """Same as database_url_from_postgres_env but raises if incomplete."""
    url = database_url_from_postgres_env()
    if not url:
        missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
        raise RuntimeError(
            "PostgreSQL env not set (use POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, "
            f"POSTGRES_PASSWORD, POSTGRES_DB). Missing: {', '.join(missing)}"
        )
    return url
