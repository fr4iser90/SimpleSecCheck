import os
from typing import Any, Dict
from urllib.parse import quote_plus


def postgres_connect_args() -> Dict[str, Any]:
    """asyncpg connect_args: ssl off for internal Docker unless POSTGRES_SSL is set."""
    v = os.environ.get("POSTGRES_SSL", "false").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return {"ssl": True}
    return {"ssl": False}


def build_database_url_from_postgres_env() -> str:
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing required DB env vars: {', '.join(missing)}")

    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    user = quote_plus(os.environ["POSTGRES_USER"])
    password = quote_plus(os.environ["POSTGRES_PASSWORD"])
    db = quote_plus(os.environ["POSTGRES_DB"])

    # No query params: asyncpg does not use libpq sslmode=...
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
