"""
Alembic env – single source of truth for schema.
URL from config.settings; runs migrations in sync context via run_sync.
"""
import asyncio
import os
import sys

# Backend root on path so "config" and "infrastructure" resolve
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = None  # we use raw SQL / op in migrations, not autogenerate from models


def get_url() -> str:
    """Database URL from config.settings; ensure async driver for async engine."""
    from config.settings import get_settings
    url = get_settings().DATABASE_URL
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL only)."""
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with async engine; run_sync for actual migration steps."""
    from config.settings import get_settings

    s = get_settings()
    connect_args = {"ssl": True} if s.POSTGRES_SSL else {"ssl": False}
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
