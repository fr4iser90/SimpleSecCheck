"""
Worker API for Scanner Discovery

Provides HTTP API for backend to query available scanners.
Worker reads scanners from database (scanner writes directly to DB).
"""
import json
import asyncio
import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import docker.errors

from worker.infrastructure.docker_adapter import DockerAdapter
from worker.infrastructure.logging_config import get_logger
from worker.infrastructure.database_adapter import PostgreSQLAdapter

logger = get_logger("worker.api.scanner")
router = APIRouter(prefix="/api/scanners", tags=["scanners"])

# Global database adapter (set by init_router)
_database_adapter: Optional[PostgreSQLAdapter] = None

# Cache for scanner list with TTL
_scanner_cache: Optional[List[Dict[str, Any]]] = None
_cache_timestamp: Optional[float] = None
_cache_lock = asyncio.Lock()  # Lock to prevent race conditions when fetching scanners

# Cache TTL in seconds (default: 1 hour, configurable via env var)
CACHE_TTL_SECONDS = int(os.getenv("SCANNER_CACHE_TTL_SECONDS", "3600"))  # 1 hour default


def init_router(database_adapter: PostgreSQLAdapter) -> APIRouter:
    """Initialize router with database adapter."""
    global _database_adapter
    _database_adapter = database_adapter
    return router


async def _check_scanners_table_exists() -> bool:
    """Check if the scanners table exists in the database."""
    if not _database_adapter:
        return False
    
    try:
        async with _database_adapter.get_session() as session:
            result = await session.execute(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": "public.scanners"}
            )
            table_exists = result.scalar() is not None
            return table_exists
    except Exception as e:
        logger.debug(f"Failed to check if scanners table exists: {e}")
        return False


async def _get_scanners_from_database() -> List[Dict[str, Any]]:
    """Get scanner list from database. If database is empty, trigger scanner container to populate it."""
    if not _database_adapter:
        raise HTTPException(status_code=503, detail="Database adapter not initialized")
    
    # Check if scanners table exists first
    table_exists = await _check_scanners_table_exists()
    if not table_exists:
        logger.warning("Scanners table does not exist yet, waiting for database initialization...")
        raise HTTPException(
            status_code=503,
            detail="Database tables not initialized yet. Please wait a moment and try again."
        )
    
    try:
        async with _database_adapter.get_session() as session:
            result = await session.execute(text("SELECT * FROM scanners ORDER BY priority"))
            rows = result.fetchall()
            
            # If database is empty OR scanners have no metadata, trigger scanner container to populate it
            needs_refresh = False
            if not rows:
                needs_refresh = True
                logger.info("Database is empty, triggering scanner container to populate scanner list")
            else:
                # Check if any scanner is missing metadata (migration scenario)
                for row in rows:
                    try:
                        scanner_metadata = getattr(row, 'scanner_metadata', None)
                        if scanner_metadata is None or (isinstance(scanner_metadata, str) and scanner_metadata.strip() in ['', '{}', 'null']):
                            needs_refresh = True
                            logger.info("Found scanners without metadata, triggering scanner container to populate metadata")
                            break
                    except AttributeError:
                        needs_refresh = True
                        logger.info("scanner_metadata column missing, triggering scanner container")
                        break
            
            if needs_refresh:
                await _refresh_scanners_from_container_with_retry()
                # Retry query after refresh
                result = await session.execute(text("SELECT * FROM scanners ORDER BY priority"))
                rows = result.fetchall()
                
                # Verify that scanners were actually written
                if not rows:
                    logger.error("Scanner refresh completed but no scanners found in database")
                    raise HTTPException(
                        status_code=503,
                        detail="Failed to populate scanners. Please try again or check logs."
                    )
            
            scanners = []
            for row in rows:
                # Convert row to dict
                scanner_dict = {
                    "name": row.name,
                    "scan_types": row.scan_types if isinstance(row.scan_types, list) else json.loads(row.scan_types) if row.scan_types else [],
                    "priority": row.priority,
                    "requires_condition": row.requires_condition,
                    "enabled": row.enabled,
                }
                
                # Extract metadata (description, categories, icon, assets)
                # Handle case where scanner_metadata column doesn't exist yet (migration pending)
                try:
                    scanner_metadata = getattr(row, 'scanner_metadata', None)
                    if scanner_metadata is None:
                        metadata = {}
                    elif isinstance(scanner_metadata, dict):
                        metadata = scanner_metadata
                    else:
                        metadata = json.loads(scanner_metadata) if scanner_metadata else {}
                except (AttributeError, KeyError, json.JSONDecodeError):
                    # Column doesn't exist yet or invalid JSON, use empty metadata
                    metadata = {}
                scanner_dict["description"] = metadata.get("description")
                scanner_dict["categories"] = metadata.get("categories", [])
                scanner_dict["icon"] = metadata.get("icon")
                scanner_dict["assets"] = metadata.get("assets", [])
                
                scanners.append(scanner_dict)
            
            logger.info(f"Retrieved {len(scanners)} scanners from database")
            return scanners
            
    except Exception as e:
        logger.error(f"Failed to get scanners from database: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scanners from database: {str(e)}"
        )


async def _refresh_scanners_from_container_with_retry(max_retries: int = 3, initial_delay: float = 2.0) -> None:
    """Trigger scanner container to update database with latest scanner list, with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            # Check if table exists before attempting refresh
            table_exists = await _check_scanners_table_exists()
            if not table_exists:
                if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Scanners table not ready yet, waiting {delay}s before retry {attempt}/{max_retries}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Scanners table not initialized after multiple retries. Database may not be ready."
                    )
            
            # Table exists, proceed with refresh
            await _refresh_scanners_from_container()
            
            # Verify refresh succeeded by checking if scanners were written
            async with _database_adapter.get_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM scanners"))
                count = result.scalar()
                if count == 0:
                    raise Exception("Scanner refresh completed but no scanners found in database")
            
            logger.info(f"Scanner refresh succeeded (attempt {attempt}/{max_retries})")
            return
            
        except HTTPException:
            raise
        except Exception as e:
            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning(f"Scanner refresh failed (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Scanner refresh failed after {max_retries} attempts: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to refresh scanners after {max_retries} attempts: {str(e)}"
                )


async def _refresh_scanners_from_container() -> None:
    """Trigger scanner container to update database with latest scanner list."""
    docker_adapter = DockerAdapter()
    if not docker_adapter.client:
        logger.error("Docker client not available")
        raise HTTPException(status_code=503, detail="Docker not available")
    
    try:
        import os
        scanner_image = "simpleseccheck-scanner:local"
        
        # Get DATABASE_URL from environment (passed to scanner container)
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=503, detail="DATABASE_URL not set")
        
        logger.info(f"Starting scanner container to refresh scanner list in database")
        container_name = f"scanner-refresh-{int(time.time())}"
        
        # Find the actual network name (Docker Compose adds project prefix)
        # Look for network containing "app" in its name (e.g., simpleseccheck_app)
        network_name = None
        try:
            networks = await asyncio.to_thread(docker_adapter.client.networks.list)
            for net in networks:
                # Match networks like "simpleseccheck_app" or just "app"
                if net.name.endswith("_app") or net.name == "app":
                    network_name = net.name
                    logger.info(f"Found network: {network_name}")
                    break
            if not network_name:
                # Fallback: try to find any network with "app" in the name
                for net in networks:
                    if "app" in net.name.lower():
                        network_name = net.name
                        logger.info(f"Found network (fallback): {network_name}")
                        break
        except Exception as e:
            logger.warning(f"Failed to find network: {e}")
        
        if not network_name:
            raise HTTPException(
                status_code=503,
                detail="Could not find Docker network. Make sure docker-compose networks are created."
            )
        
        # Create container with --list command and DATABASE_URL
        # Use same network as DB so scanner can resolve 'postgres' hostname
        container = await asyncio.to_thread(
            docker_adapter.client.containers.create,
            image=scanner_image,
            command=["python3", "-m", "scanner.core.orchestrator", "--list"],
            name=container_name,
            detach=False,
            auto_remove=False,
            network=network_name,
            environment={"DATABASE_URL": database_url}
        )
        
        container.start()
        exit_code_dict = container.wait(timeout=30)
        exit_code = exit_code_dict.get('StatusCode', 1) if isinstance(exit_code_dict, dict) else exit_code_dict
        
        # Get logs before removing container (for debugging)
        logs_text = "No logs available"
        try:
            logs = container.logs(stdout=True, stderr=True, tail=100)
            logs_text = logs.decode('utf-8') if logs else "No logs available"
        except Exception as e:
            logger.warning(f"Failed to read container logs: {e}")
        
        # Remove container
        try:
            container.remove()
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")
        
        if exit_code != 0:
            logger.error(f"Scanner container failed with exit code {exit_code}. Logs:\n{logs_text}")
            raise HTTPException(
                status_code=503,
                detail=f"Scanner container failed with exit code {exit_code}. Check worker logs for details."
            )
        
        logger.info("Scanner list refreshed in database")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh scanners from container: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to refresh scanners: {str(e)}"
        )


def _is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL."""
    global _scanner_cache, _cache_timestamp
    
    if _scanner_cache is None or _cache_timestamp is None:
        return False
    
    age_seconds = time.time() - _cache_timestamp
    is_valid = age_seconds < CACHE_TTL_SECONDS
    
    if not is_valid:
        logger.debug(f"Cache expired (age: {age_seconds:.0f}s, TTL: {CACHE_TTL_SECONDS}s)")
    
    return is_valid


@router.get("/")
async def get_scanners(scan_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get list of available scanners from database, optionally filtered by scan type.
    
    Uses cache with TTL to avoid multiple database queries.
    Cache is automatically revalidated after CACHE_TTL_SECONDS (default: 1 hour).
    """
    global _scanner_cache, _cache_timestamp
    
    try:
        # Use lock to prevent multiple simultaneous fetches
        async with _cache_lock:
            # Check if cache is valid (exists and not expired)
            if not _is_cache_valid():
                if _scanner_cache is None:
                    logger.info("Cache miss - fetching scanners from database")
                else:
                    age_seconds = time.time() - _cache_timestamp
                    logger.info(f"Cache expired ({age_seconds:.0f}s old, TTL: {CACHE_TTL_SECONDS}s) - refreshing")
                
                _scanner_cache = await _get_scanners_from_database()
                _cache_timestamp = time.time()
                logger.info(f"Scanner cache refreshed, will expire in {CACHE_TTL_SECONDS}s")
            else:
                age_seconds = time.time() - _cache_timestamp
                remaining_seconds = CACHE_TTL_SECONDS - age_seconds
                logger.debug(f"Using cached scanner list (age: {age_seconds:.0f}s, expires in {remaining_seconds:.0f}s)")
        
        scanners = _scanner_cache.copy()
        
        # Filter by scan_type if provided
        if scan_type:
            scanners = [
                s for s in scanners
                if scan_type.lower() in [st.lower() for st in s.get("scan_types", [])]
            ]
        
        return {"scanners": scanners}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get scanners", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scanners: {str(e)}"
        )


@router.post("/refresh")
async def refresh_scanners() -> Dict[str, str]:
    """Manually refresh scanner list by triggering scanner container to update database."""
    global _scanner_cache, _cache_timestamp
    
    try:
        async with _cache_lock:
            logger.info("Manually refreshing scanner list - triggering scanner container")
            await _refresh_scanners_from_container_with_retry()
            # Reload from database after refresh
            _scanner_cache = await _get_scanners_from_database()
            _cache_timestamp = time.time()
        return {"status": "ok", "count": len(_scanner_cache)}
    except Exception as e:
        logger.error("Failed to refresh scanners", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh scanners: {str(e)}"
        )


@router.get("/assets")
async def get_scanner_assets() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get list of all scanner assets from database.
    
    Assets are stored in scanner metadata in database.
    Uses cache with TTL if available, otherwise fetches fresh data.
    """
    global _scanner_cache, _cache_timestamp
    
    try:
        # Use cache if valid, otherwise fetch (with lock to prevent race conditions)
        async with _cache_lock:
            if not _is_cache_valid():
                if _scanner_cache is None:
                    logger.info("Cache miss - fetching scanners for assets")
                else:
                    logger.info("Cache expired - refreshing for assets")
                _scanner_cache = await _get_scanners_from_database()
                _cache_timestamp = time.time()
            else:
                logger.debug("Using cached scanner list for assets")
        
        scanners = _scanner_cache.copy()
        
        # Extract assets from scanners
        assets_list = []
        for scanner in scanners:
            scanner_name = scanner.get("name")
            scanner_assets = scanner.get("assets", [])
            
            for asset in scanner_assets:
                # Extract last_updated from asset dict if present (copy to avoid mutating original)
                asset_copy = asset.copy()
                last_updated = asset_copy.pop("last_updated", None)
                assets_list.append({
                    "scanner": scanner_name,
                    "asset": asset_copy,
                    "last_updated": last_updated
                })
        
        logger.info(f"Extracted {len(assets_list)} scanner assets from {len(scanners)} scanners")
        return {"assets": assets_list}
        
    except Exception as e:
        logger.error(f"Failed to get scanner assets: {e}", exc_info=True)
        return {"assets": []}
