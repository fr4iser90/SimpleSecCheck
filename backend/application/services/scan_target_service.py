"""
ScanTarget Application Service (DDD)

Orchestrates My Targets: list/create/update/delete and trigger scan.
Uses ScanTargetRepository (port) and domain validation/permission services.
"""
from typing import List, Optional, Any, Dict

from domain.entities.scan_target import ScanTarget
from domain.value_objects.auto_scan_config import AutoScanConfig
from domain.entities.target_type import TargetType
from domain.repositories.scan_target_repository import ScanTargetRepository
from domain.services.target_handlers import validate_target_source_and_config, get_target_handler
from domain.services.target_permission_policy import check_can_scan_target, get_allow_flags_from_settings
from domain.services.target_scan_helper import create_scan_from_target
from config.settings import get_settings


class ScanTargetService:
    """Application service for user scan targets (My Targets)."""

    def __init__(self, target_repository: ScanTargetRepository):
        self._repo = target_repository

    async def list_by_user(
        self,
        user_id: str,
        target_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[ScanTarget]:
        """List targets for user, optionally filtered by type."""
        return await self._repo.list_by_user(
            user_id,
            target_type=target_type,
            limit=limit,
            offset=offset,
        )

    async def get_by_id(self, target_id: str, user_id: str) -> Optional[ScanTarget]:
        """Get target by id; must belong to user."""
        return await self._repo.get_by_id(target_id, user_id)

    async def create_target(
        self,
        user_id: str,
        target_type: str,
        source: str,
        config: Dict[str, Any],
        *,
        display_name: Optional[str] = None,
        auto_scan: Optional[Dict[str, Any]] = None,
        actor_role: str = "user",
    ) -> ScanTarget:
        """
        Create a new target. Validates source/config and checks permissions.
        Raises ValueError for validation errors; callers map to HTTP 400/403.
        """
        if not TargetType.is_valid(target_type):
            raise ValueError(
                f"Invalid target type: {target_type!r}. "
                f"Valid types: {', '.join(TargetType.get_all_values())}"
            )
        settings = get_settings()
        allow_flags = get_allow_flags_from_settings(settings)
        is_admin = actor_role == "admin"
        check_can_scan_target(
            target_type=target_type,
            allow_flags=allow_flags,
            is_admin=is_admin,
            target_url=source,
        )
        validated_config = validate_target_source_and_config(
            target_type, source.strip(), config or {}
        )
        if await self._repo.exists_for_user(user_id, source.strip(), target_type):
            raise ValueError("Target with this source already added")

        target = ScanTarget(
            user_id=user_id,
            type=target_type,
            source=source.strip(),
            display_name=(display_name or "").strip() or None,
            auto_scan=AutoScanConfig.from_dict(auto_scan or {}),
            config=validated_config,
        )
        return await self._repo.create(target)

    async def update_target(
        self,
        target_id: str,
        user_id: str,
        *,
        config: Optional[Dict[str, Any]] = None,
        auto_scan: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None,
    ) -> ScanTarget:
        """
        Update an existing target. Applies only provided fields; config validated per type.
        Raises ValueError if target not found.
        """
        target = await self._repo.get_by_id(target_id, user_id)
        if not target:
            raise ValueError("Target not found")

        if config is not None:
            handler = get_target_handler(target.type)
            if handler:
                target.config = handler.validate_config(config)
            else:
                target.config = config
        if auto_scan is not None:
            target.auto_scan = AutoScanConfig.from_dict(auto_scan)
        if display_name is not None:
            target.display_name = (display_name or "").strip() or None

        return await self._repo.update(target)

    async def delete(self, target_id: str, user_id: str) -> bool:
        """Delete target. Returns True if deleted."""
        return await self._repo.delete(target_id, user_id)

    async def trigger_scan(
        self,
        target_id: str,
        user_id: str,
        *,
        metadata_extra: Optional[Dict[str, Any]] = None,
        enforcement_mode: str = "full",
    ) -> Optional[str]:
        """
        Trigger a scan for a saved target. Returns scan_id or None on failure.
        """
        target = await self._repo.get_by_id(target_id, user_id)
        if not target:
            return None
        return await create_scan_from_target(
            target,
            metadata_extra=metadata_extra or {},
            enforcement_mode=enforcement_mode,
        )
