"""
Run Alembic migrations (upgrade head). Single entry point for schema updates.
Do not use create_all or _migrate_existing_tables for schema.
"""
import asyncio
import logging
import os

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def _run_upgrade_sync() -> None:
    """Run alembic upgrade head synchronously (for use from async via run_in_executor)."""
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_ini = os.path.join(backend_root, "alembic.ini")
    if not os.path.isfile(alembic_ini):
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")
    config = Config(alembic_ini)
    config.set_main_option("script_location", os.path.join(backend_root, "alembic"))
    command.upgrade(config, "head")


async def run_alembic_upgrade() -> None:
    """Run alembic upgrade head. Call this at startup instead of create_tables."""
    try:
        await asyncio.get_event_loop().run_in_executor(None, _run_upgrade_sync)
        logger.info("Alembic upgrade head completed")
    except Exception as e:
        logger.exception("Alembic upgrade failed")
        raise
