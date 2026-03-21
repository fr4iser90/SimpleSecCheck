"""
Target Scan Helper

Create a scan from a ScanTarget (generic saved target). Used by scheduler and "Scan now" UI.
TargetType -> ScanType mapping; handler provides target_url / config.
"""
from __future__ import annotations

import logging
from typing import Optional

from domain.entities.scan_target import ScanTarget
from domain.entities.scan import ScanType
from domain.entities.target_type import TargetType
from domain.validation.target_handlers import get_target_handler
from domain.exceptions.scan_exceptions import ScanException, ScanValidationException
from application.dtos.request_dto import ScanRequestDTO
from application.services.scan_service import ScanService

logger = logging.getLogger(__name__)

TARGET_TYPE_TO_SCAN_TYPE = {
    TargetType.GIT_REPO.value: ScanType.CODE,
    TargetType.CONTAINER_REGISTRY.value: ScanType.CONTAINER,
    TargetType.LOCAL_MOUNT.value: ScanType.CODE,
    TargetType.UPLOADED_CODE.value: ScanType.CODE,
    TargetType.WEBSITE.value: ScanType.WEBSITE,
    TargetType.API_ENDPOINT.value: ScanType.WEBSITE,
    TargetType.NETWORK_HOST.value: ScanType.NETWORK,
    TargetType.KUBERNETES_CLUSTER.value: ScanType.NETWORK,
}


async def _get_default_scanners_for_scan_type(scan_type: ScanType) -> list[str]:
    from infrastructure.container import get_scanner_repository
    repo = get_scanner_repository()
    scanners = await repo.list_all()
    enabled = [s for s in scanners if s.enabled]
    ordered = sorted(enabled, key=lambda x: -x.priority)
    scan_type_str = scan_type.value.lower()
    names = [
        s.name for s in ordered
        if s.scan_types and scan_type_str in [st.lower() for st in (s.scan_types or [])]
    ]
    if not names:
        logger.warning("No scanners found for scan_type=%s, using code as fallback", scan_type.value)
        names = [
            s.name for s in ordered
            if s.scan_types and "code" in [st.lower() for st in (s.scan_types or [])]
        ]
    return names


async def get_default_scanner_names_for_target_type(target_type: str) -> list[str]:
    if not TargetType.is_valid(target_type):
        return []
    scan_type = TARGET_TYPE_TO_SCAN_TYPE.get(target_type, ScanType.CODE)
    return await _get_default_scanners_for_scan_type(scan_type)


async def create_scan_from_target(
    target: ScanTarget,
    *,
    metadata_extra: Optional[dict] = None,
    config_override: Optional[dict] = None,
    enforcement_mode: str = "full",
) -> str:
    handler = get_target_handler(target.type)
    if not handler:
        raise ScanValidationException(f"No scan handler for target type {target.type!r}")

    scan_type = TARGET_TYPE_TO_SCAN_TYPE.get(target.type, ScanType.CODE)
    target_for_scan = target
    if config_override:
        from dataclasses import replace
        merged = dict(target.config or {})
        merged.update(config_override)
        target_for_scan = replace(target, config=merged)

    params = handler.prepare_scan_params(target_for_scan)
    target_url = params.get("target_url", target.source)
    config = params.get("config") or target_for_scan.config

    custom_scanners = (
        target_for_scan.config.get("scanners")
        if isinstance(target_for_scan.config, dict)
        else None
    )
    if isinstance(custom_scanners, list) and custom_scanners:
        scanners = custom_scanners
    else:
        scanners = await _get_default_scanners_for_scan_type(scan_type)
    if not scanners:
        raise ScanValidationException(
            f"No enabled scanners available for scan type '{scan_type.value}'. "
            "Enable at least one scanner for this type in Admin → Scanner / Tool settings."
        )

    display = target.display_name or target.source
    name = f"Scan: {display[:80]}" if len(display) > 80 else f"Scan: {display}"
    scan_metadata = {
        "source": "auto_scan_target",
        "target_id": target.id,
        "target_type": target.type,
        **(metadata_extra or {}),
    }

    request = ScanRequestDTO(
        name=name,
        description=f"Auto-scan for target {target.type}: {target.source[:100]}",
        scan_type=scan_type,
        target_url=target_url,
        target_type=target.type,
        user_id=target.user_id,
        scanners=scanners,
        config=config,
        metadata=scan_metadata,
        tags=["auto-scan", "saved-target"],
    )

    try:
        from infrastructure.container import get_scan_service
        scan_service: ScanService = get_scan_service()
        scan_dto = await scan_service.create_scan(
            request,
            actor_role="user",
            enforcement_mode=enforcement_mode,
        )
        logger.info("Created scan %s for target %s (%s: %s)", scan_dto.id, target.id, target.type, target.source[:50])
        return scan_dto.id
    except ScanException:
        raise
    except Exception as e:
        logger.error("Failed to create scan from target %s: %s", target.id, e, exc_info=True)
        raise ScanValidationException(f"Failed to create scan: {e}") from e
