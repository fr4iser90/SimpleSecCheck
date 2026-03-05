"""
Scanner Assets Routes
Generic endpoints for scanner assets and updates
"""
import os
from fastapi import APIRouter, HTTPException
import httpx
from app.services.shutdown_service import update_activity


router = APIRouter()


@router.get("/api/scanners/assets")
async def get_scanner_assets():
    update_activity()
    if os.getenv("SCANNER_PROXY_MODE", "false").lower() == "true":
        worker_url = os.getenv("SCANNER_WORKER_API_URL", "http://scanner-worker:8080/api/scanners/assets")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(worker_url)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Worker asset proxy failed: {exc}")

    from app.services.scanner_assets_service import list_scanner_assets
    return {"assets": list_scanner_assets()}


@router.post("/api/scanners/{scanner_name}/assets/{asset_id}/update")
async def update_asset(scanner_name: str, asset_id: str):
    update_activity()
    if os.getenv("SCANNER_PROXY_MODE", "false").lower() == "true":
        worker_url = os.getenv(
            "SCANNER_WORKER_ASSET_UPDATE_URL",
            f"http://scanner-worker:8080/api/scanners/{scanner_name}/assets/{asset_id}/update",
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(worker_url)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Worker asset update failed: {exc}")

    worker_url = os.getenv(
        "SCANNER_WORKER_ASSET_UPDATE_URL",
        f"http://scanner-worker:8080/api/scanners/{scanner_name}/assets/{asset_id}/update",
    )
    from app.services.scanner_asset_update_service import start_asset_update
    try:
        return await start_asset_update(scanner_name, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/scanners/assets/update/status")
async def get_update_status():
    update_activity()
    if os.getenv("SCANNER_PROXY_MODE", "false").lower() == "true":
        worker_url = os.getenv(
            "SCANNER_WORKER_ASSET_STATUS_URL",
            "http://scanner-worker:8080/api/scanners/assets/update/status",
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(worker_url)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Worker asset status failed: {exc}")

    from app.services.scanner_asset_update_service import get_asset_update_status
    return get_asset_update_status()
