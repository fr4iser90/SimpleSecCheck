"""
Jobs API for worker - cancel by scan_id.
"""
from fastapi import APIRouter, HTTPException

from worker.domain.job_execution.services.job_orchestration_service import JobOrchestrationService


def init_jobs_router(job_orchestration_service: JobOrchestrationService) -> APIRouter:
    """Create jobs router with cancel endpoint."""
    router = APIRouter(prefix="/api/jobs", tags=["jobs"])

    @router.post("/cancel/{scan_id}")
    async def cancel_job_by_scan_id(scan_id: str):
        """Signal worker to stop the running container for this scan_id."""
        stopped = await job_orchestration_service.stop_job_by_scan_id(scan_id)
        return {"scan_id": scan_id, "stopped": stopped}

    return router
