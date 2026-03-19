"""
Scanner API Routes

Dynamic scanner discovery and configuration endpoints.
Backend calls Worker API, which calls Scanner container with --list.
Scanners are stored in database for faster access.
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from api.deps.actor_context import get_actor_context, ActorContext
import httpx

from config.settings import get_settings
from api.routes.admin import get_system_state_repository_dependency
from domain.repositories.system_state_repository import SystemStateRepository
from domain.services.target_permission_policy import (
    DANGEROUS_TARGETS,
    TARGET_SECURITY_LEVEL,
    TARGET_PERMISSION_MAP,
    get_allow_flags_from_settings,
    get_allowed_targets_for_frontend,
    get_allowed_targets_display,
    effective_target_labels_for_role,
)
from domain.services.role_capabilities_merge import merge_role_capabilities_raw
from infrastructure.logging_config import get_logger
from infrastructure.container import get_scanner_repository, run_database_migrations
from domain.repositories.scanner_repository import ScannerRepository

logger = get_logger("api.scanners")


def get_scanner_repository_dependency() -> ScannerRepository:
    return get_scanner_repository()

router = APIRouter(prefix="/api/scanners", tags=["scanners"])
config_router = APIRouter(prefix="/api", tags=["config"])


# Pydantic models for responses
class ScannerResponse(BaseModel):
    name: str
    scan_types: List[str]
    priority: int
    requires_condition: Optional[str] = None
    enabled: bool
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    icon: Optional[str] = None


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
    auth_mode: str  # "free" | "basic" | "jwt"
    access_mode: str  # "public" | "mixed" | "private"
    login_required: bool
    features: Dict[str, Any]  # Product/UI features only
    scan_types: Dict[str, Any]  # Catalog of scan types (code, image, ...)
    allowed_targets: Dict[str, bool]  # What may be scanned (local_paths, git_repos, ...)
    allowed_targets_display: List[str]  # Human-readable labels for allowed targets (for UI help text)
    permissions: Dict[str, Any]  # RBAC: dangerous_targets, target_security_level, target_permission_map
    queue: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    scan_defaults: Optional[Dict[str, Any]] = None  # default_finding_policy_path, finding_policy_apply_by_default


class RoleCapabilitiesSnapshot(BaseModel):
    """Public snapshot for one role: effective capabilities on this instance."""
    allowed_scan_targets: List[str] = Field(
        description="Scan target types allowed (role config ∩ instance feature flags), human-readable labels",
    )
    my_targets: bool = Field(description="Whether this role may use My Targets (saved targets)")
    bulk_scan: bool = Field(description="Whether bulk scan tab is available for this role")
    scanner_access: str = Field(
        description="all_enabled = any scanner the instance offers; limited = subset configured by admin",
    )


class PublicCapabilitiesAuthSnippet(BaseModel):
    allow_self_registration: bool
    login_required: bool
    access_mode: str
    auth_mode: str


class PublicCapabilitiesResponse(BaseModel):
    """Guest vs signed-in user capabilities for marketing / transparency (backend-driven)."""
    guest: RoleCapabilitiesSnapshot
    user: RoleCapabilitiesSnapshot
    auth: PublicCapabilitiesAuthSnippet
    help: str = Field(description="Short explanation for UI")


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


async def _sync_scanners_to_db(scanners_data: List[Dict[str, Any]], scanner_repository: ScannerRepository):
    """Sync scanners from worker to database via ScannerRepository."""
    try:
        await scanner_repository.sync_all(scanners_data)
        logger.info(f"Synced {len(scanners_data)} scanners to database")
    except Exception as e:
        logger.error(f"Failed to sync scanners to database: {e}")
        raise


@router.get("/", response_model=Dict[str, List[ScannerResponse]])
async def get_scanners(
    scan_type: Optional[str] = Query(None, description="Filter by scan type (code, image, website, network)"),
    scanner_repository: ScannerRepository = Depends(get_scanner_repository_dependency),
):
    """Get list of available scanners from database, optionally filtered by scan type."""
    try:
        if not await scanner_repository.table_exists():
            logger.info("Scanners table does not exist, creating tables...")
            await run_database_migrations()
        db_scanners = await scanner_repository.list_all()
        needs_refresh = False
        if not db_scanners:
            needs_refresh = True
            logger.info("No scanners in database, triggering scanner container to populate")
        elif db_scanners[0].last_discovered_at:
            age_seconds = (datetime.utcnow() - db_scanners[0].last_discovered_at).total_seconds()
            if age_seconds > 3600:
                needs_refresh = True
                logger.info(f"Scanners in database are stale ({age_seconds:.0f}s old), triggering refresh")
        if needs_refresh:
            try:
                worker_url = os.getenv("WORKER_API_URL", "http://worker:8081")
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"{worker_url}/api/scanners/refresh", timeout=30.0)
                    if response.status_code != 200:
                        logger.warning(f"Failed to refresh scanners via worker: {response.status_code}")
                db_scanners = await scanner_repository.list_all()
            except Exception as e:
                logger.warning(f"Failed to refresh scanners, using cached data: {e}")
        scanner_list = []
        for scanner in db_scanners:
            if scan_type:
                if scan_type.lower() not in [st.lower() for st in scanner.scan_types]:
                    continue
            try:
                metadata = scanner.scanner_metadata if isinstance(scanner.scanner_metadata, dict) else {}
            except (AttributeError, KeyError):
                metadata = {}
            
            scanner_list.append(ScannerResponse(
                name=scanner.name,
                scan_types=scanner.scan_types,
                priority=scanner.priority,
                requires_condition=scanner.requires_condition,
                enabled=scanner.enabled,
                description=metadata.get("description"),
                categories=metadata.get("categories", []),
                icon=metadata.get("icon")
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
    Get list of all scanner assets from manifests (generic: any scanner with assets, e.g. vuln DBs).
    
    Fetches assets from worker API (worker has access to scanner code).
    Each asset may expose update.enabled; auto_update is controlled by config (scanner_assets_auto_update_enabled).
    Future: response could include health/reachability per scanner (e.g. SonarQube server, Docker daemon).
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
async def start_asset_update(
    scanner_name: str,
    asset_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
):
    """
    Start update for a specific scanner asset. Admin only.
    
    Verifies asset exists via worker API, then queues update job to worker.
    """
    if actor_context.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may trigger scanner asset updates",
        )
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


def _default_scan_defaults_for_config() -> Dict[str, Any]:
    return {
        "default_finding_policy_path": ".scanning/finding-policy.json",
        "finding_policy_apply_by_default": True,
    }


@config_router.get("/config/capabilities", response_model=PublicCapabilitiesResponse)
async def get_public_capabilities(
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
) -> PublicCapabilitiesResponse:
    """
    Public comparison: effective capabilities for guest (no login) vs signed-in user.
    Merges role_capabilities from system config with instance feature flags.
    """
    try:
        from config.settings import load_settings_from_database

        settings = get_settings()
        await load_settings_from_database(settings)
        state = await system_state_repo.get_singleton()
        cfg = state.config if state else None
        merged = merge_role_capabilities_raw(cfg if isinstance(cfg, dict) else None)
        allow_flags = get_allow_flags_from_settings(settings)
        bulk_on = True  # matches features.bulk_scan in /api/config
        bulk_guests = getattr(settings, "BULK_SCAN_ALLOW_GUESTS", False)

        def _snapshot(role: str, is_guest: bool) -> RoleCapabilitiesSnapshot:
            r = merged[role]
            labels = effective_target_labels_for_role(r["allowed_target_types"], allow_flags)
            keys = r.get("allowed_scanner_tools_keys") or []
            scanner_access = "all_enabled" if not keys else "limited"
            return RoleCapabilitiesSnapshot(
                allowed_scan_targets=labels,
                my_targets=bool(r.get("my_targets_allowed")),
                bulk_scan=bulk_on and (not is_guest or bulk_guests),
                scanner_access=scanner_access,
            )

        access_mode = getattr(settings, "ACCESS_MODE", "public")
        return PublicCapabilitiesResponse(
            guest=_snapshot("guest", True),
            user=_snapshot("user", False),
            auth=PublicCapabilitiesAuthSnippet(
                allow_self_registration=getattr(settings, "ALLOW_SELF_REGISTRATION", False),
                login_required=access_mode == "private",
                access_mode=access_mode,
                auth_mode=settings.AUTH_MODE.lower(),
            ),
            help=(
                "Guest = using the app without an account. User = signed in. "
                "Scan targets are the intersection of admin role settings and instance feature flags. "
                "Admins may have additional options not shown here."
            ),
        )
    except Exception as e:
        logger.error("Failed to get public capabilities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}",
        )


@config_router.get("/config", response_model=FrontendConfigResponse)
async def get_frontend_config(
    system_state_repo: SystemStateRepository = Depends(get_system_state_repository_dependency),
):
    """
    Get frontend configuration from settings.
    
    Uses dynamic settings - NO HARDCODING!
    """
    try:
        from config.settings import load_settings_from_database
        settings = get_settings()
        await load_settings_from_database(settings)
        scan_defaults = dict(_default_scan_defaults_for_config())
        try:
            state = await system_state_repo.get_singleton()
            if state and state.config and state.config.get("scan_defaults"):
                scan_defaults.update(state.config["scan_defaults"])
        except Exception:
            pass
        
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
        
        # Features: product/UI only (no targets, no RBAC)
        features = {
            "bulk_scan": True,  # TODO: Add setting
            "bulk_scan_allow_guests": getattr(settings, "BULK_SCAN_ALLOW_GUESTS", False),
            "session_management": True,
            "metadata_collection": "optional",
            "zip_upload": settings.ALLOW_ZIP_UPLOAD,
            "scanner_assets_auto_update_enabled": getattr(settings, "SCANNER_ASSETS_AUTO_UPDATE_ENABLED", False),
            "allow_self_registration": getattr(settings, "ALLOW_SELF_REGISTRATION", False),
        }
        # Allowed targets: from single source (target_permission_policy)
        _allow_flags = get_allow_flags_from_settings(settings)
        allowed_targets = get_allowed_targets_for_frontend(_allow_flags)
        allowed_targets_display = get_allowed_targets_display(_allow_flags)
        # Permissions: RBAC (who may scan what)
        permissions = {
            "dangerous_targets": list(DANGEROUS_TARGETS),
            "target_security_level": dict(TARGET_SECURITY_LEVEL),
            "target_permission_map": dict(TARGET_PERMISSION_MAP),
        }
        queue = {
            "strategy": getattr(settings, "QUEUE_STRATEGY", "fifo"),
            "max_length": 100,  # TODO: Add setting
            "public_view": False,  # TODO: Add setting
        }
        rate_limits = {
            "scans_per_session": 10,  # TODO: Add setting
            "requests_per_session": 100,  # TODO: Add setting
        }
        access_mode = getattr(settings, "ACCESS_MODE", "public")
        return FrontendConfigResponse(
            auth_mode=settings.AUTH_MODE.lower(),
            access_mode=access_mode,
            login_required=access_mode == "private",
            features=features,
            scan_types=scan_types_config,
            allowed_targets=allowed_targets,
            allowed_targets_display=allowed_targets_display,
            permissions=permissions,
            queue=queue,
            rate_limits=rate_limits,
            scan_defaults=scan_defaults,
        )
        
    except Exception as e:
        logger.error("Failed to get frontend config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get frontend config: {str(e)}"
        )
