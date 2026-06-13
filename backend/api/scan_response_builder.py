"""Build scan API responses including measured duration estimates."""
from typing import Dict, List, Optional

from application.dtos.scan_dto import ScanDTO
from api.schemas.scan_schemas import ScanResponseSchema
from domain.repositories.scan_repository import ScanRepository
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


async def compute_queue_estimates(
    scan_id: str,
    scanners: Optional[List[str]],
    status,
    scan_repository: ScanRepository,
) -> Dict[str, Optional[int]]:
    """
    Queue-related estimates for a scan.

    - estimated_time_seconds: measured duration of this scan (pending/running only)
    - estimated_wait_seconds: sum of measured durations for scans ahead in queue
    - queue_position: 1-based position while pending/running, else null
    """
    status_val = _status_value(status)
    estimated_time_seconds: Optional[int] = None
    estimated_wait_seconds: Optional[int] = None
    queue_position: Optional[int] = None

    if status_val not in ("pending", "running"):
        return {
            "estimated_time_seconds": None,
            "estimated_wait_seconds": None,
            "queue_position": None,
        }

    estimated_time_seconds = await estimated_time_seconds_for_scanners(
        scanners,
        status=status,
    )
    queue_position = await scan_repository.get_position_in_queue(scan_id)

    if queue_position and queue_position > 1:
        scans_before = await scan_repository.get_scans_before_in_queue(scan_id)
        wait_total = 0.0
        has_estimate = False
        for s in scans_before:
            sc = getattr(s, "scanners", None) or []
            if not sc:
                continue
            est = await ScannerDurationService.get_estimated_time(sc)
            if est is not None:
                wait_total += est
                has_estimate = True
        estimated_wait_seconds = int(wait_total) if has_estimate else None

    return {
        "estimated_time_seconds": estimated_time_seconds,
        "estimated_wait_seconds": estimated_wait_seconds,
        "queue_position": queue_position,
    }


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
