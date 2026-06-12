"""Build scan API responses including measured duration estimates."""
from typing import Optional, List

from application.dtos.scan_dto import ScanDTO
from api.schemas.scan_schemas import ScanResponseSchema
from domain.services.scanner_duration_service import ScannerDurationService


def _status_value(status) -> str:
    return (getattr(status, "value", status) or "").lower()


async def estimated_time_seconds_for_scanners(
    scanners: Optional[List[str]],
    *,
    status,
) -> Optional[int]:
    """Measured estimate for pending/running scans; None if incomplete or not applicable."""
    names = [s for s in (scanners or []) if s and str(s).strip()]
    if not names:
        return None
    if _status_value(status) not in ("pending", "running"):
        return None
    est = await ScannerDurationService.get_estimated_time(names)
    return int(est) if est is not None else None


async def estimated_time_seconds_for_scan_dto(scan_dto: ScanDTO) -> Optional[int]:
    return await estimated_time_seconds_for_scanners(
        scan_dto.scanners,
        status=scan_dto.status,
    )


async def scan_dto_to_response(scan_dto: ScanDTO) -> ScanResponseSchema:
    estimated = await estimated_time_seconds_for_scan_dto(scan_dto)
    return ScanResponseSchema(
        id=scan_dto.id,
        name=scan_dto.name,
        description=scan_dto.description,
        scan_type=scan_dto.scan_type,
        target_url=scan_dto.target_url,
        target_type=scan_dto.target_type,
        user_id=scan_dto.user_id,
        project_id=scan_dto.project_id,
        status=scan_dto.status,
        created_at=scan_dto.created_at,
        started_at=scan_dto.started_at,
        completed_at=scan_dto.completed_at,
        scheduled_at=scan_dto.scheduled_at,
        tags=scan_dto.tags,
        total_vulnerabilities=scan_dto.total_vulnerabilities,
        critical_vulnerabilities=scan_dto.critical_vulnerabilities,
        high_vulnerabilities=scan_dto.high_vulnerabilities,
        medium_vulnerabilities=scan_dto.medium_vulnerabilities,
        low_vulnerabilities=scan_dto.low_vulnerabilities,
        info_vulnerabilities=scan_dto.info_vulnerabilities,
        metadata=scan_dto.metadata,
        estimated_time_seconds=estimated,
    )
