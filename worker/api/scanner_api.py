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
        exit_code = container.wait(timeout=30)
        logger.info(f"Container exited with code: {exit_code}")
        
        # Get logs before container is removed
        logs = container.logs(stdout=True, stderr=True)
        output = logs.decode('utf-8') if logs else ""
        
        # Remove container manually after reading logs
        try:
            container.remove()
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")
        
        # Log first 500 chars of output for debugging
        if output:
            logger.debug(f"Container output (first 500 chars): {output[:500]}")
        else:
            logger.warning("Container produced no output")
        
        # Check exit code but continue anyway - JSON might still be in output
        if exit_code != 0:
            logger.warning(f"Container exited with non-zero code {exit_code}. Output preview: {output[:1000]}")
            # Continue anyway - JSON might still be in output despite warnings
        
        if not output:
            raise ValueError("No output from scanner container")
        
        # Extract JSON from output (might have extra lines and be multiline)
        # The JSON structure is: {"scanners": [{...}, {...}, ...]}
        # We need to capture the entire root object, not stop at the first scanner
        lines = output.strip().split('\n')
        json_lines = []
        found_json_start = False
        brace_count = 0
        
        for line in lines:
            stripped = line.strip()
            # Skip entrypoint messages and warnings
            if (not stripped or
                stripped.startswith('[') or 
                stripped.startswith('Entrypoint') or 
                stripped.startswith('error:') or 
                stripped.startswith('WARNING:') or 
                stripped.startswith('ls:') or
                stripped.startswith('drwx')):
                continue
            
            # Start collecting when we find opening brace (root object)
            if stripped.startswith('{') and not found_json_start:
                found_json_start = True
                json_lines = [stripped]
                # Count braces: opening braces increase count, closing braces decrease
                brace_count = stripped.count('{') - stripped.count('}')
                continue
            
            # Collect lines while we're in the JSON object
            if found_json_start:
                json_lines.append(stripped)
                # Update brace count: +1 for each {, -1 for each }
                brace_count += stripped.count('{') - stripped.count('}')
                
                # Stop when we've closed the root object (brace_count == 0)
                # This means all opening braces have been matched with closing braces
                if brace_count == 0:
                    break
        
        if not json_lines:
            logger.error(f"Could not find JSON in output. Full output (first 2000 chars): {output[:2000]}")
            raise ValueError(f"Could not find JSON in output. Output preview: {output[:500]}")
        
        json_line = '\n'.join(json_lines)
        
        # Debug: Log the collected JSON to understand what we're parsing
        logger.debug(f"Collected JSON ({len(json_lines)} lines, {len(json_line)} chars). First 500 chars: {json_line[:500]}")
        logger.debug(f"Collected JSON last 500 chars: {json_line[-500:]}")
        
        try:
            data = json.loads(json_line)
            scanner_count = len(data.get("scanners", []))
            logger.info(f"Successfully parsed {scanner_count} scanners from container output")
            # Return scanners with their assets included
            return data.get("scanners", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}. JSON (first 1000 chars): {json_line[:1000]}")
            logger.error(f"JSON (last 1000 chars): {json_line[-1000:]}")
            logger.error(f"JSON length: {len(json_line)} chars, brace_count when stopped: {brace_count}")
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
