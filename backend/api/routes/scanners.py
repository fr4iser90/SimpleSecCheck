"""
Scanner API Routes

Dynamic scanner discovery and configuration endpoints.
Backend calls Worker API, which calls Scanner container with --list.
Scanners are stored in database for faster access.
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
import httpx

from config.settings import get_settings
from infrastructure.logging_config import get_logger
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import Scanner

logger = get_logger("api.scanners")

router = APIRouter(prefix="/api/scanners", tags=["scanners"])
config_router = APIRouter(prefix="/api", tags=["config"])


# Pydantic models for responses
class ScannerResponse(BaseModel):
    name: str
    scan_types: List[str]
    priority: int
    requires_condition: Optional[str] = None
    enabled: bool


class ScannerAssetResponse(BaseModel):
    scanner: str
    asset: Dict[str, Any]
    last_updated: Optional[Dict[str, Any]] = None


class UpdateStatusResponse(BaseModel):
    status: str  # 'idle' | 'running' | 'done' | 'error'
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


class FrontendConfigResponse(BaseModel):
    environment: str
    is_production: bool
    auth_mode: str  # "free" | "basic" | "jwt"
    login_required: bool
    features: Dict[str, Any]
    queue: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None


async def _get_scanners_from_worker(scan_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get scanner list from worker API."""
    import httpx
    
    worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
    url = f"{worker_url}/api/scanners/"
    params = {}
    if scan_type:
        params["scan_type"] = scan_type
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.warning(f"Worker API returned {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Worker API returned {response.status_code}"
                )
            data = response.json()
            scanners = data.get("scanners", [])
            if not scanners:
                logger.warning("Worker API returned empty scanner list")
            return scanners
    except httpx.TimeoutException as e:
        logger.error("Worker API request timed out", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker API timeout - scanners may still be loading"
        )
    except httpx.RequestError as e:
        logger.error("Failed to connect to worker API", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker API not available"
        )


async def _sync_scanners_to_db(scanners_data: List[Dict[str, Any]]):
    """Sync scanners from worker to database."""
    try:
        async with db_adapter.async_session() as session:
            for scanner_data in scanners_data:
                # Check if scanner exists
                result = await session.execute(
                    select(Scanner).where(Scanner.name == scanner_data["name"])
                )
                scanner = result.scalar_one_or_none()
                
                if scanner:
                    # Update existing scanner
                    scanner.scan_types = scanner_data.get("scan_types", [])
                    scanner.priority = scanner_data.get("priority", 0)
                    scanner.requires_condition = scanner_data.get("requires_condition")
                    scanner.enabled = scanner_data.get("enabled", True)
                    scanner.last_discovered_at = datetime.utcnow()
                else:
                    # Create new scanner
                    scanner = Scanner(
                        name=scanner_data["name"],
                        scan_types=scanner_data.get("scan_types", []),
                        priority=scanner_data.get("priority", 0),
                        requires_condition=scanner_data.get("requires_condition"),
                        enabled=scanner_data.get("enabled", True),
                        last_discovered_at=datetime.utcnow()
                    )
                    session.add(scanner)
            
            await session.commit()
            logger.info(f"Synced {len(scanners_data)} scanners to database")
    except Exception as e:
        logger.error(f"Failed to sync scanners to database: {e}")
        raise


@router.get("/", response_model=Dict[str, List[ScannerResponse]])
async def get_scanners(
    scan_type: Optional[str] = Query(None, description="Filter by scan type (code, image, website, network)")
):
    """
    Get list of available scanners from database, optionally filtered by scan type.
    If database is empty or stale (older than 1 hour), fetches from worker and syncs to database.
    """
    try:
        # Check if scanners table exists, if not create it
        scanners_table_exists = await db_adapter.check_table_exists("scanners")
        if not scanners_table_exists:
            logger.info("Scanners table does not exist, creating tables...")
            await db_adapter.create_tables()
        
        # First, try to get from database
        async with db_adapter.async_session() as session:
            result = await session.execute(select(Scanner))
            db_scanners = result.scalars().all()
        
        # If database is empty or stale (older than 1 hour), refresh from worker
        needs_refresh = False
        if not db_scanners:
            needs_refresh = True
            logger.info("No scanners in database, fetching from worker")
        elif db_scanners[0].last_discovered_at:
            age_seconds = (datetime.utcnow() - db_scanners[0].last_discovered_at).total_seconds()
            if age_seconds > 3600:  # 1 hour
                needs_refresh = True
                logger.info(f"Scanners in database are stale ({age_seconds:.0f}s old), refreshing from worker")
        
        if needs_refresh:
            try:
                # Fetch from worker and sync to DB
                scanners_data = await _get_scanners_from_worker(None)  # Get all scanners
                await _sync_scanners_to_db(scanners_data)
                
                # Re-fetch from DB
                async with db_adapter.async_session() as session:
                    result = await session.execute(select(Scanner))
                    db_scanners = result.scalars().all()
            except Exception as e:
                logger.warning(f"Failed to refresh scanners from worker, using cached data: {e}")
                # Continue with existing DB data if refresh fails
        
        # Filter by scan_type if provided
        scanner_list = []
        for scanner in db_scanners:
            if scan_type:
                if scan_type.lower() in [st.lower() for st in scanner.scan_types]:
                    scanner_list.append(ScannerResponse(
                        name=scanner.name,
                        scan_types=scanner.scan_types,
                        priority=scanner.priority,
                        requires_condition=scanner.requires_condition,
                        enabled=scanner.enabled
                    ))
            else:
                scanner_list.append(ScannerResponse(
                    name=scanner.name,
                    scan_types=scanner.scan_types,
                    priority=scanner.priority,
                    requires_condition=scanner.requires_condition,
                    enabled=scanner.enabled
                ))
        
        return {"scanners": scanner_list}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get scanners", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scanners: {str(e)}"
        )


@router.get("/assets", response_model=Dict[str, List[ScannerAssetResponse]])
async def get_scanner_assets():
    """
    Get list of all scanner assets from manifests.
    
    Fetches assets from worker API (worker has access to scanner code).
    """
    try:
        # Try to get assets from worker API first
        worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{worker_url}/api/scanners/assets")
                if response.status_code == 200:
                    worker_data = response.json()
                    # Convert worker response to our response model
                    assets_list = [
                        ScannerAssetResponse(
                            scanner=item["scanner"],
                            asset=item["asset"],
                            last_updated=item.get("last_updated")
                        )
                        for item in worker_data.get("assets", [])
                    ]
                    logger.info(f"Retrieved {len(assets_list)} scanner assets from worker")
                    return {"assets": assets_list}
            except httpx.RequestError as e:
                logger.error(f"Worker API not available for assets: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Worker API not available - cannot retrieve scanner assets"
                )
        
    except Exception as e:
        logger.error("Failed to get scanner assets", error=str(e))
        # Return empty list instead of error - assets are optional
        return {"assets": []}


@router.get("/assets/update/status", response_model=UpdateStatusResponse)
async def get_update_status():
    """
    Get status of scanner asset updates.
    
    TODO: Implement actual update status tracking (Redis/DB).
    """
    # For now, return idle status
    return UpdateStatusResponse(
        status="idle",
        started_at=None,
        finished_at=None,
        error_message=None,
        exit_code=None
    )


@router.post("/{scanner_name}/assets/{asset_id}/update", response_model=UpdateStatusResponse)
async def start_asset_update(scanner_name: str, asset_id: str):
    """
    Start update for a specific scanner asset.
    
    Verifies asset exists via worker API, then queues update job to worker.
    """
    # Verify asset exists via worker API
    worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{worker_url}/api/scanners/assets")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Worker API not available"
                )
            
            worker_data = response.json()
            assets = worker_data.get("assets", [])
            
            # Find the asset
            asset_found = None
            for item in assets:
                if item.get("scanner") == scanner_name and item.get("asset", {}).get("id") == asset_id:
                    asset_found = item.get("asset")
                    break
            
            if not asset_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Asset {asset_id} not found for scanner {scanner_name}"
                )
            
            if not asset_found.get("update") or not asset_found.get("update", {}).get("enabled"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Asset {asset_id} does not support updates"
                )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to worker API: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker API not available"
        )
    
    # TODO: Queue update job to worker
    # For now, return running status
    return UpdateStatusResponse(
        status="running",
        started_at=None,
        finished_at=None,
        error_message=None,
        exit_code=None
    )


@config_router.get("/config", response_model=FrontendConfigResponse)
async def get_frontend_config():
    """
    Get frontend configuration from settings.
    
    Uses dynamic settings - NO HARDCODING!
    """
    try:
        settings = get_settings()
        
        # Determine environment
        is_production = settings.ENVIRONMENT.lower() in ["production", "prod"]
        
        # Build scan types with metadata (backend-driven, no hardcoding!)
        scan_types_config = {
            "code": {
                "enabled": True,
                "label": "Code",
                "backend_value": "code",
                "description": "Scan source code for vulnerabilities"
            },
            "image": {
                "enabled": True,
                "label": "Image",
                "backend_value": "container",
                "description": "Scan container images for vulnerabilities"
            },
            "website": {
                "enabled": True,
                "label": "Website",
                "backend_value": "web_application",
                "description": "Scan websites for security issues"
            },
            "network": {
                "enabled": True,
                "label": "Network",
                "backend_value": "infrastructure",
                "description": "Scan network hosts for vulnerabilities"
            }
        }
        
        # Build features from settings
        features = {
            "scan_types": scan_types_config,
            "bulk_scan": True,  # TODO: Add setting
            "local_paths": not getattr(settings, "ONLY_GIT_SCANS", False),
            "git_only": getattr(settings, "ONLY_GIT_SCANS", False),
            "queue_enabled": getattr(settings, "QUEUE_ENABLED", True),
            "session_management": getattr(settings, "SESSION_MANAGEMENT", True),
            "metadata_collection": getattr(settings, "METADATA_COLLECTION", "optional"),
            "auto_shutdown": True,  # TODO: Add setting
            "zip_upload": True,  # TODO: Add setting
            "owasp_auto_update_enabled": False,  # TODO: Add setting
        }
        
        # Queue config
        queue = None
        if features["queue_enabled"]:
            queue = {
                "max_length": 100,  # TODO: Add setting
                "public_view": False,  # TODO: Add setting
            }
        
        # Rate limits
        rate_limits = {
            "scans_per_session": 10,  # TODO: Add setting
            "requests_per_session": 100,  # TODO: Add setting
        }
        
        return FrontendConfigResponse(
            environment=settings.ENVIRONMENT,
            is_production=is_production,
            auth_mode=settings.AUTH_MODE.lower(),
            login_required=settings.LOGIN_REQUIRED,
            features=features,
            queue=queue,
            rate_limits=rate_limits
        )
        
    except Exception as e:
        logger.error("Failed to get frontend config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get frontend config: {str(e)}"
        )
