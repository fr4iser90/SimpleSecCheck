"""
Worker API for Scanner Discovery

Provides HTTP API for backend to query available scanners.
Worker calls scanner container with --list to get scanner info.
"""
import json
import asyncio
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import docker.errors
from pathlib import Path
import os

from worker.infrastructure.docker_adapter import DockerAdapter
from worker.infrastructure.logging_config import get_logger

logger = get_logger("worker.api.scanner")
router = APIRouter(prefix="/api/scanners", tags=["scanners"])

# Cache for scanner list with TTL
_scanner_cache: Optional[List[Dict[str, Any]]] = None
_cache_timestamp: Optional[float] = None
_cache_lock = asyncio.Lock()  # Lock to prevent race conditions when fetching scanners

# Cache TTL in seconds (default: 1 hour, configurable via env var)
CACHE_TTL_SECONDS = int(os.getenv("SCANNER_CACHE_TTL_SECONDS", "3600"))  # 1 hour default


async def _get_scanners_from_container() -> List[Dict[str, Any]]:
    """Get scanner list by running scanner container with --list flag."""
    docker_adapter = DockerAdapter()
    if not docker_adapter.client:
        logger.error("Docker client not available")
        raise HTTPException(status_code=503, detail="Docker not available")
    
    try:
        # Get scanner image name from environment or use default
        scanner_image = "simpleseccheck-scanner:local"
        
        logger.info(f"Creating scanner container with image: {scanner_image}")
        # Generate a readable container name
        import time
        container_name = f"scanner-list-{int(time.time())}"
        
        # Create container with --list command
        container = await asyncio.to_thread(
            docker_adapter.client.containers.create,
            image=scanner_image,
            command=["python3", "-m", "scanner.core.orchestrator", "--list"],
            name=container_name,
            detach=False,
            auto_remove=False,  # Don't auto-remove so we can read logs
            network_mode="bridge"
        )
        
        logger.info(f"Starting scanner container: {container.id}")
        # Start container and wait for completion
        container.start()
        
        logger.info("Waiting for container to complete (timeout: 30s)...")
        exit_code_dict = container.wait(timeout=30)
        exit_code = exit_code_dict.get('StatusCode', 1) if isinstance(exit_code_dict, dict) else exit_code_dict
        logger.info(f"Container exited with code: {exit_code}")
        
        # Read JSON from stdout ONLY (stderr=False = no logs in output)
        # Scanner outputs: Logs → stderr, JSON → stdout
        # NOTE: Entrypoint script may write to stdout, so we need to extract JSON
        logs = container.logs(stdout=True, stderr=False)
        stdout_text = logs.decode('utf-8').strip() if logs else ""
        
        if not stdout_text:
            raise ValueError("No output from scanner container")
        
        if exit_code != 0:
            # If exit code is non-zero, read stderr for error details
            error_logs = container.logs(stdout=False, stderr=True)
            error_output = error_logs.decode('utf-8') if error_logs else ""
            raise ValueError(f"Container exited with non-zero code {exit_code}. Error: {error_output[:1000]}")
        
        # Extract JSON from stdout (skip entrypoint messages)
        # JSON starts with '{', find first occurrence
        json_start = stdout_text.find('{')
        if json_start == -1:
            raise ValueError(f"No JSON found in stdout. Output: {stdout_text[:500]}")
        
        json_data = stdout_text[json_start:].strip()
        
        # Remove container manually after reading data
        try:
            container.remove()
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")
        
        # Parse JSON
        try:
            data = json.loads(json_data)
            scanner_count = len(data.get("scanners", []))
            logger.info(f"Successfully parsed {scanner_count} scanners from container")
            # Return scanners with their assets included
            return data.get("scanners", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}. JSON (first 1000 chars): {json_data[:1000] if json_data else 'None'}")
            logger.error(f"JSON (last 1000 chars): {json_data[-1000:] if json_data else 'None'}")
            logger.error(f"JSON length: {len(json_data)} chars")
            raise ValueError(f"Invalid JSON from scanner container: {str(e)}")
        
    except HTTPException:
        raise
    except docker.errors.ImageNotFound:
        logger.error(f"Scanner image not found: {scanner_image}")
        raise HTTPException(
            status_code=503,
            detail=f"Scanner image '{scanner_image}' not found. Please build it with: docker compose build scanner"
        )
    except docker.errors.APIError as e:
        logger.error(f"Docker API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Docker API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to get scanners from container: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get scanners: {str(e)}"
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
    Get list of available scanners, optionally filtered by scan type.
    
    Worker calls scanner container with --list to get scanner info.
    Uses cache with TTL to avoid multiple container calls.
    Cache is automatically revalidated after CACHE_TTL_SECONDS (default: 1 hour).
    """
    global _scanner_cache, _cache_timestamp
    
    try:
        # Use lock to prevent multiple simultaneous fetches
        async with _cache_lock:
            # Check if cache is valid (exists and not expired)
            if not _is_cache_valid():
                if _scanner_cache is None:
                    logger.info("Cache miss - fetching scanners from container")
                else:
                    age_seconds = time.time() - _cache_timestamp
                    logger.info(f"Cache expired ({age_seconds:.0f}s old, TTL: {CACHE_TTL_SECONDS}s) - refreshing")
                
                _scanner_cache = await _get_scanners_from_container()
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
    """Manually refresh scanner cache by querying scanner container again."""
    global _scanner_cache, _cache_timestamp
    
    try:
        async with _cache_lock:
            logger.info("Manually refreshing scanner cache")
            _scanner_cache = await _get_scanners_from_container()
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
    Get list of all scanner assets.
    
    Assets are extracted from scanner --list output (scanner provides everything).
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
                _scanner_cache = await _get_scanners_from_container()
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
