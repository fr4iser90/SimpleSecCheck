"""
Setup Status Service

Provides setup status (tables, admin user, system state) and DB migrations.
Uses repositories + database adapter for a single place to check/setup.
"""
from typing import Any, Dict

from domain.repositories.user_repository import UserRepository
from domain.repositories.system_state_repository import SystemStateRepository


class SetupStatusService:
    """Service for setup status and database migrations."""

    def __init__(
        self,
        user_repository: UserRepository,
        system_state_repository: SystemStateRepository,
    ):
        self._user_repository = user_repository
        self._system_state_repository = system_state_repository

    async def get_setup_status(self) -> Dict[str, Any]:
        """Return setup status (tables, admin exists, system state, DB connected)."""
        from infrastructure.database.adapter import db_adapter

        tables_exist = await db_adapter.check_tables_exist()
        admin_exists = await self._user_repository.has_admin_user()
        state = await self._system_state_repository.get_singleton()
        system_state_exists = state is not None
        all_tables_exist = len(tables_exist) > 0 and all(tables_exist.values())
        setup_complete = (
            all_tables_exist and admin_exists and system_state_exists
        )
        return {
            "setup_complete": setup_complete,
            "tables": tables_exist,
            "admin_user_exists": admin_exists,
            "system_state_exists": system_state_exists,
            "database_connected": await db_adapter.test_connection(),
        }

    async def run_migrations(self) -> None:
        """Run database migrations (Alembic upgrade head)."""
        from infrastructure.database.adapter import db_adapter
        await db_adapter.create_tables()
