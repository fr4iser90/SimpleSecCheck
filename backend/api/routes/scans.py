"""
Scans API Routes

This module defines the FastAPI routes for scan operations.
Routes support both authenticated and guest users via ActorContext.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi import status as fastapi_status
import asyncio
import json
import secrets
from urllib.parse import quote
import ipaddress
import re
from pathlib import Path

from api.deps.actor_context import get_actor_context, ActorContext
from api.schemas.scan_schemas import (
    ScanRequestSchema,
    ScanResponseSchema,
    ScanSummarySchema,
    ScanUpdateSchema,
    ScanFilterSchema,
    ScanStatisticsSchema,
    ScannerDurationStatSchema,
    CancelScanSchema,
    BatchScanSchema,
    ScanStatusResponseSchema,
    AggregatedResultSchema,
    ReportShareLinkRequestSchema,
    ReportShareLinkResponseSchema,
)
from application.services.scan_service import ScanService
from application.dtos.scan_dto import ScanDTO
from application.dtos.request_dto import (
    ScanRequestDTO,
    ScanUpdateRequestDTO,
    ScanFilterDTO,
    CancelScanRequestDTO,
)
from domain.exceptions.scan_exceptions import (
    ScanException,
    ScanNotFoundException,
    ScanValidationException,
    ScanConcurrencyLimitException,
    FeatureDisabledException,
    TargetPermissionDeniedException,
    ScanExecutionRateLimitException,
    ScanPolicyBlockedException,
)
from domain.entities.scan import ScanType
from domain.services.target_permission_policy import check_can_scan_target, get_allow_flags_from_settings
from domain.services.scan_result_access import can_read_scan_results, is_scan_owner
from config.settings import get_settings
from typing import Annotated
import re


# Import dependency injection container
from infrastructure.container import get_scan_service, get_scan_steps_repository
from domain.entities.target_type import TargetType


def _determine_target_type(scan_type: ScanType, target_url: str) -> str:
    """
    Automatically determine target_type from scan_type and target_url.
    This function centralizes target type detection logic - NO HARDCODING in frontend!
    Uses TargetType enum for type safety.
    """
    if not target_url or not target_url.strip():
        return TargetType.LOCAL_MOUNT.value
    
    target = target_url.strip()
    
    # Git URL patterns
    git_patterns = [
        r'^https?://(www\.)?(github|gitlab)\.com/[\w\-\.]+/[\w\-\.]+',
        r'^git@(github|gitlab)\.com:[\w\-\.]+/[\w\-\.]+\.git$',
        r'\.git$',
    ]
    is_git_url = any(re.match(pattern, target, re.IGNORECASE) for pattern in git_patterns)
    
    # Container registry pattern (simplified)
    container_pattern = r'^(?:[a-zA-Z0-9.-]+(?::\d+)?/)?[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[\w][\w.-]{0,127})?(?:@sha256:[a-f0-9]{64})?$'
    is_container = not target.startswith(('http://', 'https://', '/', './', '../')) and re.match(container_pattern, target)
    
    # Local path
    is_local_path = target.startswith(('/', './', '../'))
    
    # Network host detection (IP address or hostname without protocol)
    is_network_host = False
    if not target.startswith(('http://', 'https://', '/', './', '../')):
        # Check if it's an IP address (IPv4 or IPv6)
        try:
            ipaddress.ip_address(target.split(':')[0])  # Remove port if present
            is_network_host = True
        except ValueError:
            # Check if it's a hostname (contains dots, no slashes, not a container image pattern)
            if '.' in target and '/' not in target and ':' not in target.split('.')[-1]:
                # Simple heuristic: if it looks like a hostname and not a container image
                if not re.match(container_pattern, target):
                    is_network_host = True
    
    # Determine based on scan_type - using TargetType enum values
    if scan_type == ScanType.CODE:
        if is_git_url:
            return TargetType.GIT_REPO.value
        elif is_container:
            return TargetType.CONTAINER_REGISTRY.value
        elif is_local_path:
            return TargetType.LOCAL_MOUNT.value
        else:
            return TargetType.UPLOADED_CODE.value
    elif scan_type == ScanType.CONTAINER:
        return TargetType.CONTAINER_REGISTRY.value
    elif scan_type == ScanType.WEB_APPLICATION:
        if target.startswith(('http://', 'https://')):
            return TargetType.WEBSITE.value
        else:
            return TargetType.API_ENDPOINT.value
    elif scan_type == ScanType.INFRASTRUCTURE:
        return TargetType.NETWORK_HOST.value
    elif scan_type == ScanType.NETWORK:
        return TargetType.NETWORK_HOST.value
    else:
        # Default: Git repo if URL detected, otherwise local mount
        return TargetType.GIT_REPO.value if is_git_url else TargetType.LOCAL_MOUNT.value


def _get_target_type_info(target_type: str) -> dict:
    """
    Get display information for a target type.
    Returns: dict with display_name, icon, action, cleanup (optional)
    Uses TargetType enum for type safety.
    """
    # Validate target_type first
    if not TargetType.is_valid(target_type):
        return {
            "display_name": target_type,
            "icon": "📋",
            "action": "Will be scanned"
        }
    
    # Map TargetType enum values to display information
    info_map = {
        TargetType.GIT_REPO.value: {
            "display_name": "Git Repository",
            "icon": "🔗",
            "action": "Repository will be automatically cloned",
            "cleanup": "Temporary project will be deleted after scan"
        },
        TargetType.CONTAINER_REGISTRY.value: {
            "display_name": "Container Registry",
            "icon": "🐳",
            "action": "Container image will be scanned"
        },
        TargetType.LOCAL_MOUNT.value: {
            "display_name": "Local Mount",
            "icon": "📁",
            "action": "Local path will be scanned directly"
        },
        TargetType.UPLOADED_CODE.value: {
            "display_name": "Uploaded Code",
            "icon": "📦",
            "action": "Uploaded code will be scanned"
        },
        TargetType.WEBSITE.value: {
            "display_name": "Website",
            "icon": "🌐",
            "action": "Website will be scanned"
        },
        TargetType.API_ENDPOINT.value: {
            "display_name": "API Endpoint",
            "icon": "🔌",
            "action": "API endpoint will be scanned"
        },
        TargetType.NETWORK_HOST.value: {
            "display_name": "Network Host",
            "icon": "🌐",
            "action": "Network host will be scanned"
        },
        TargetType.KUBERNETES_CLUSTER.value: {
            "display_name": "Kubernetes Cluster",
            "icon": "☸️",
            "action": "Kubernetes cluster will be scanned"
        },
        TargetType.APK.value: {
            "display_name": "Android APK",
            "icon": "📱",
            "action": "Android APK will be scanned"
        },
        TargetType.IPA.value: {
            "display_name": "iOS IPA",
            "icon": "📱",
            "action": "iOS IPA will be scanned"
        },
        TargetType.OPENAPI_SPEC.value: {
            "display_name": "OpenAPI Spec",
            "icon": "📄",
            "action": "OpenAPI specification will be scanned"
        }
    }
    return info_map.get(target_type, {
        "display_name": target_type,
        "icon": "📋",
        "action": "Will be scanned"
    })

# Import test container for testing
import os
if os.environ.get("ENVIRONMENT") == "test":
    from tests.unit.test_container import get_test_scan_service


def get_scan_service_dependency():
    """Get the appropriate scan service dependency based on environment."""
    if os.environ.get("ENVIRONMENT") == "test":
        return get_test_scan_service()
    return get_scan_service()


router = APIRouter(
    prefix="/api/v1/scans",
    tags=["scans"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Unprocessable Entity"},
        500: {"description": "Internal Server Error"},
    },
)


def _scan_user_id_str(dto: ScanDTO) -> Optional[str]:
    if dto.user_id in (None, ""):
        return None
    return str(dto.user_id)


def _require_scan_read(
    dto: ScanDTO,
    actor: ActorContext,
    share_token: Optional[str] = None,
) -> None:
    if not can_read_scan_results(
        metadata=dto.metadata or {},
        scan_user_id=_scan_user_id_str(dto),
        actor_user_id=actor.user_id,
        actor_session_id=actor.session_id,
        actor_is_authenticated=bool(actor.is_authenticated),
        share_token_query=share_token,
    ):
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


def _require_scan_owner(dto: ScanDTO, actor: ActorContext) -> None:
    if not is_scan_owner(
        metadata=dto.metadata or {},
        scan_user_id=_scan_user_id_str(dto),
        actor_user_id=actor.user_id,
        actor_session_id=actor.session_id,
        actor_is_authenticated=bool(actor.is_authenticated),
    ):
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Only the scan owner can do this",
        )


def _read_deduplicated_steps(scan_id: str) -> tuple[List[Dict[str, Any]], int, int]:
    """
    Read and deduplicate steps from steps.log file.
    Returns: (steps_list, total_steps, completed_steps)
    """
    from config.settings import settings
    
    results_dir = Path(settings.RESULTS_DIR_HOST if hasattr(settings, 'RESULTS_DIR_HOST') else "/app/results")
    steps_log_path = results_dir / scan_id / "logs" / "steps.log"
    
    if not steps_log_path.exists():
        return [], 0, 0
    
    # Use a dict to track the latest status for each step number
    steps_dict = {}
    try:
        with open(steps_log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('{"init"'):
                    continue
                try:
                    step_data = json.loads(line)
                    # Filter out init messages and only include actual step entries
                    if "step_name" in step_data or "name" in step_data:
                        step_number = step_data.get("number")
                        if step_number is not None:
                            # Get timestamp for comparison
                            timestamp_str = step_data.get("timestamp", "")
                            # Keep the entry with the latest timestamp for each step number
                            if step_number not in steps_dict:
                                steps_dict[step_number] = step_data
                            else:
                                # Compare timestamps to keep the latest
                                existing_timestamp = steps_dict[step_number].get("timestamp", "")
                                if timestamp_str > existing_timestamp:
                                    steps_dict[step_number] = step_data
                except json.JSONDecodeError:
                    continue
    except Exception:
        return [], 0, 0
    
    # Convert dict to sorted list by step number
    steps = [steps_dict[key] for key in sorted(steps_dict.keys())]
    
    for step in steps:
        _enrich_step_duration_fields(step)
    
    # Calculate progress
    total_steps = len(steps)
    completed_steps = sum(1 for step in steps if step.get("status") in ["completed", "failed"])
    
    return steps, total_steps, completed_steps


def _enrich_step_duration_fields(step: Dict[str, Any]) -> None:
    """Mutate step dict with duration_seconds (same logic as steps.log path)."""
    import time
    from datetime import datetime, timezone
    started_at = step.get("started_at")
    completed_at = step.get("completed_at")
    if started_at and completed_at:
        try:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(completed_at).replace("Z", "+00:00"))
            step["duration_seconds"] = max(0, int((end - start).total_seconds()))
        except (ValueError, TypeError, AttributeError, OSError):
            step["duration_seconds"] = None
    elif started_at and step.get("status") == "running":
        try:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            step["duration_seconds"] = max(0, int(time.time() - start.timestamp()))
        except (ValueError, TypeError, AttributeError, OSError):
            step["duration_seconds"] = None
    else:
        step["duration_seconds"] = None
    to = step.get("timeout_seconds")
    if to is not None:
        try:
            step["timeout_seconds"] = int(to)
        except (ValueError, TypeError):
            step["timeout_seconds"] = None


@router.post(
    "/",
    response_model=ScanResponseSchema,
    status_code=fastapi_status.HTTP_201_CREATED,
    summary="Create a new scan",
    description="Create and start a new security scan. Supports both authenticated and guest users.",
    response_description="Created scan information",
)
async def create_scan(
    scan_request: ScanRequestSchema,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanResponseSchema:
    """
    Create a new scan.
    
    - **scan_request**: Scan creation parameters
    - **actor_context**: Resolved user/session context (auto-injected)
    - **scan_service**: Scan orchestration service (auto-injected)
    """
    try:
        # Prepare metadata - add session_id for guest sessions
        metadata = scan_request.metadata.copy() if scan_request.metadata else {}
        if not actor_context.is_authenticated and actor_context.session_id:
            # Store session_id in metadata for guest sessions
            metadata["session_id"] = actor_context.session_id
        
        # Auto-determine target_type if not provided
        target_type = scan_request.target_type
        if not target_type:
            target_type = _determine_target_type(scan_request.scan_type, scan_request.target_url)
        
        # Feature flag + permission check (local/dangerous targets require admin)
        is_admin = actor_context.role == "admin"
        settings = get_settings()
        check_can_scan_target(
            target_type,
            allow_flags=get_allow_flags_from_settings(settings),
            is_admin=is_admin,
            target_url=scan_request.target_url,
        )
        
        # Default priority by role (admin > user > guest) when queue strategy uses priority
        if actor_context.role == "admin":
            default_priority = getattr(settings, "QUEUE_PRIORITY_ADMIN", 10)
        elif actor_context.is_authenticated:
            default_priority = getattr(settings, "QUEUE_PRIORITY_USER", 5)
        else:
            default_priority = getattr(settings, "QUEUE_PRIORITY_GUEST", 1)
        # Convert request schema to DTO
        request_dto = ScanRequestDTO(
            name=scan_request.name,
            description=scan_request.description,
            scan_type=scan_request.scan_type,
            target_url=scan_request.target_url,
            target_type=target_type,
            user_id=actor_context.user_id if actor_context.is_authenticated else None,
            project_id=scan_request.project_id,
            config=scan_request.config.dict() if scan_request.config else None,
            scanners=scan_request.scanners,
            scheduled_at=scan_request.scheduled_at,
            tags=scan_request.tags,
            metadata=metadata,
            priority=default_priority,
        )
        
        # Create scan via service
        scan_dto = await scan_service.create_scan(
            request_dto,
            actor_role=actor_context.role,
            guest_session_id=(
                actor_context.session_id if not actor_context.is_authenticated else None
            ),
        )
        
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
        )
        
    except ScanConcurrencyLimitException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except ScanExecutionRateLimitException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(getattr(e, "retry_after_seconds", 3600))},
        )
    except ScanPolicyBlockedException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FeatureDisabledException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except TargetPermissionDeniedException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ScanValidationException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=List[ScanSummarySchema],
    summary="List scans",
    description="List scans with optional filtering and pagination. Returns scan summaries.",
    response_description="List of scan summaries",
)
async def list_scans(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    scan_type: Optional[str] = Query(None, description="Filter by scan type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> List[ScanSummarySchema]:
    """
    List scans with filtering.
    
    - **user_id**: Filter by user ID (defaults to current actor)
    - **project_id**: Filter by project ID
    - **status**: Filter by scan status
    - **scan_type**: Filter by scan type
    - **tags**: Filter by tags
    - **limit**: Number of results to return
    - **offset**: Offset for pagination
    - **sort_by**: Field to sort by
    - **sort_order**: Sort direction (asc/desc)
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        if actor_context.is_authenticated:
            filter_dto = ScanFilterDTO(
                user_id=actor_context.user_id,
                guest_session_id=None,
                project_id=project_id,
                status=status,
                scan_type=scan_type,
                tags=tags,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        else:
            if not actor_context.session_id:
                return []
            filter_dto = ScanFilterDTO(
                user_id=None,
                guest_session_id=actor_context.session_id,
                project_id=project_id,
                status=status,
                scan_type=scan_type,
                tags=tags,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        
        scan_summaries = await scan_service.list_scans(filter_dto)
        
        return [
            ScanSummarySchema(
                id=summary.id,
                name=summary.name,
                scan_type=summary.scan_type,
                target_url=summary.target_url,
                target_type=summary.target_type,
                status=summary.status,
                created_at=summary.created_at,
                started_at=summary.started_at,
                completed_at=summary.completed_at,
                total_vulnerabilities=summary.total_vulnerabilities,
                critical_vulnerabilities=summary.critical_vulnerabilities,
                high_vulnerabilities=summary.high_vulnerabilities,
                user_id=summary.user_id,
                project_id=summary.project_id,
                tags=summary.tags,
            )
            for summary in scan_summaries
        ]
        
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def _detect_scan_type_from_target(target_url: str) -> str:
    """
    Automatically detect scan_type from target_url without requiring user selection.
    Returns: scan_type string (code, image, website, network)
    """
    if not target_url or not target_url.strip():
        return "code"  # Default to code for empty targets
    
    target = target_url.strip()
    
    # Git URL patterns → Code
    git_patterns = [
        r'^https?://(www\.)?(github|gitlab)\.com/[\w\-\.]+/[\w\-\.]+',
        r'^git@(github|gitlab)\.com:[\w\-\.]+/[\w\-\.]+\.git$',
        r'\.git$',
    ]
    is_git_url = any(re.match(pattern, target, re.IGNORECASE) for pattern in git_patterns)
    if is_git_url:
        return "code"
    
    # Local path → Code
    if target.startswith(('/', './', '../')):
        return "code"
    
    # Container registry pattern → Image
    container_pattern = r'^(?:[a-zA-Z0-9.-]+(?::\d+)?/)?[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[\w][\w.-]{0,127})?(?:@sha256:[a-f0-9]{64})?$'
    is_container = not target.startswith(('http://', 'https://', '/', './', '../')) and re.match(container_pattern, target)
    if is_container:
        return "image"
    
    # Network host (IP or hostname without protocol) → Network
    if not target.startswith(('http://', 'https://', '/', './', '../')):
        try:
            ipaddress.ip_address(target.split(':')[0])  # Remove port if present
            return "network"
        except ValueError:
            # Check if it's a hostname (contains dots, no slashes, not a container image)
            if '.' in target and '/' not in target and ':' not in target.split('.')[-1]:
                if not re.match(container_pattern, target):
                    return "network"
    
    # http:// or https:// → Website
    if target.startswith(('http://', 'https://')):
        return "website"
    
    # Default to code
    return "code"


@router.get(
    "/detect-scan-type",
    summary="Detect scan type from target",
    description="Automatically detect scan_type from target_url. Returns suggested scan_type and target_type info.",
)
async def detect_scan_type(
    target_url: str = Query(..., description="Target URL or path"),
) -> dict:
    """
    Automatically detect scan_type from target_url.
    Returns: suggested scan_type and target_type information.
    """
    try:
        # Detect scan type
        suggested_scan_type = _detect_scan_type_from_target(target_url)
        
        # Convert to ScanType enum for target type detection
        scan_type_enum = ScanType(suggested_scan_type) if hasattr(ScanType, suggested_scan_type.upper()) else ScanType.CODE
        try:
            scan_type_enum = next((st for st in ScanType if st.value == suggested_scan_type), ScanType.CODE)
        except (ValueError, AttributeError):
            scan_type_enum = ScanType.CODE
        
        # Determine target type
        target_type = _determine_target_type(scan_type_enum, target_url)
        
        # Get display information
        info = _get_target_type_info(target_type)
        
        return {
            "suggested_scan_type": suggested_scan_type,
            "target_type": target_type,
            "display_name": info["display_name"],
            "icon": info["icon"],
            "action": info["action"],
            "cleanup": info.get("cleanup"),
            "target_url": target_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to detect scan type: {str(e)}"
        )


@router.get(
    "/detect-target-type",
    summary="Detect target type",
    description="Detect target type from scan_type and target_url. Returns display information for frontend.",
)
async def detect_target_type(
    scan_type: str = Query(..., description="Scan type (code, image, website, network)"),
    target_url: str = Query(..., description="Target URL or path"),
) -> dict:
    """
    Detect target type and return display information.
    Used by frontend to show appropriate UI based on detected target type.
    """
    try:
        # Convert string to ScanType enum
        try:
            scan_type_enum = ScanType(scan_type) if hasattr(ScanType, scan_type.upper()) else ScanType.CODE
        except (ValueError, AttributeError):
            # Try by value if enum name lookup failed
            scan_type_enum = next((st for st in ScanType if st.value == scan_type), ScanType.CODE)
        
        # Determine target type
        target_type = _determine_target_type(scan_type_enum, target_url)
        
        # Get display information
        info = _get_target_type_info(target_type)
        
        return {
            "target_type": target_type,
            "display_name": info["display_name"],
            "icon": info["icon"],
            "action": info["action"],
            "cleanup": info.get("cleanup"),
            "target_url": target_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to detect target type: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=ScanStatisticsSchema,
    summary="Get scan statistics",
    description="Get statistics about scans for the current user or all users (admin only).",
    response_description="Scan statistics",
)
async def get_scan_statistics(
    user_id: Optional[str] = Query(None, description="Get stats for specific user (admin only)"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanStatisticsSchema:
    """
    Get scan statistics.

    - **user_id**: Optional user ID to get stats for (admin only)
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        # Non-admin users can only get their own stats
        stats_user_id = None
        if user_id:
            if not actor_context.is_authenticated:
                raise HTTPException(
                    status_code=fastapi_status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            stats_user_id = user_id
        else:
            if actor_context.is_authenticated:
                stats_user_id = actor_context.user_id

        statistics_dto = await scan_service.get_scan_statistics(stats_user_id)

        return ScanStatisticsSchema(
            total_scans=statistics_dto.total_scans,
            pending_scans=statistics_dto.pending_scans,
            running_scans=statistics_dto.running_scans,
            completed_scans=statistics_dto.completed_scans,
            failed_scans=statistics_dto.failed_scans,
            cancelled_scans=statistics_dto.cancelled_scans,
            total_vulnerabilities=statistics_dto.total_vulnerabilities,
            critical_vulnerabilities=statistics_dto.critical_vulnerabilities,
            high_vulnerabilities=statistics_dto.high_vulnerabilities,
            medium_vulnerabilities=statistics_dto.medium_vulnerabilities,
            low_vulnerabilities=statistics_dto.low_vulnerabilities,
            info_vulnerabilities=statistics_dto.info_vulnerabilities,
            repository_scans=statistics_dto.repository_scans,
            container_scans=statistics_dto.container_scans,
            infrastructure_scans=statistics_dto.infrastructure_scans,
            web_application_scans=statistics_dto.web_application_scans,
            average_scan_duration=statistics_dto.average_scan_duration,
            longest_scan_duration=statistics_dto.longest_scan_duration,
            shortest_scan_duration=statistics_dto.shortest_scan_duration,
            scanner_duration_stats=[
                ScannerDurationStatSchema(
                    scanner_name=s["scanner_name"],
                    avg_duration_seconds=s["avg_duration_seconds"],
                    min_duration_seconds=s.get("min_duration_seconds"),
                    max_duration_seconds=s.get("max_duration_seconds"),
                    sample_count=s["sample_count"],
                    last_updated=s.get("last_updated"),
                )
                for s in statistics_dto.scanner_duration_stats
            ],
        )

    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{scan_id}",
    response_model=ScanResponseSchema,
    summary="Get scan by ID",
    description="Get detailed information about a specific scan.",
    response_description="Scan details",
)
async def get_scan(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanResponseSchema:
    """
    Get scan by ID.
    
    - **scan_id**: ID of the scan to retrieve
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_read(scan_dto, actor_context)

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
        )

    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put(
    "/{scan_id}",
    response_model=ScanResponseSchema,
    summary="Update scan",
    description="Update scan information (name, description, tags, etc.).",
    response_description="Updated scan information",
)
async def update_scan(
    scan_id: str,
    update_request: ScanUpdateSchema,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanResponseSchema:
    """
    Update scan information.
    
    - **scan_id**: ID of the scan to update
    - **update_request**: Update parameters
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        existing = await scan_service.get_scan_by_id(scan_id)
        _require_scan_owner(existing, actor_context)

        update_dto = ScanUpdateRequestDTO(
            name=update_request.name,
            description=update_request.description,
            status=update_request.status.value if update_request.status else None,
            config=update_request.config.dict() if update_request.config else None,
            tags=update_request.tags,
            metadata=update_request.metadata,
        )

        scan_dto = await scan_service.update_scan(scan_id, update_dto)
        
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
        )
        
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ScanValidationException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{scan_id}",
    status_code=fastapi_status.HTTP_204_NO_CONTENT,
    summary="Delete scan",
    description="Delete a scan and its results.",
    response_description="Scan deleted successfully",
)
async def delete_scan(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> None:
    """
    Delete a scan.
    
    - **scan_id**: ID of the scan to delete
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_owner(scan_dto, actor_context)

        success = await scan_service.delete_scan(scan_id)
        if not success:
            raise HTTPException(
                status_code=fastapi_status.HTTP_404_NOT_FOUND,
                detail="Scan not found"
            )
        
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{scan_id}/status",
    response_model=ScanStatusResponseSchema,
    summary="Get scan status",
    description="Get current status and progress of a scan.",
    response_description="Scan status information",
)
async def get_scan_status(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanStatusResponseSchema:
    """
    Get scan status.
    
    - **scan_id**: ID of the scan
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_read(scan_dto, actor_context)
        status_info = await scan_service.get_scan_status(scan_id)

        return ScanStatusResponseSchema(
            scan_id=status_info["scan_id"],
            status=status_info["status"],
            progress=status_info["progress"],
            started_at=status_info["started_at"],
            completed_at=status_info["completed_at"],
            duration=status_info["duration"],
            vulnerabilities_found=status_info["vulnerabilities_found"],
            metadata=status_info["metadata"],
        )

    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{scan_id}/steps",
    summary="Get scan steps status",
    description=(
        "Step progress: read from PostgreSQL scan_steps when the scanner mirrors there "
        "(POSTGRES_* in scan container for DB mirror); otherwise steps.log."
    ),
    response_description="Step status information",
)
async def get_scan_steps(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> Dict[str, Any]:
    """
    Get scan steps status.

    Primary source: ``scan_steps`` table (one row per step, no log dedup).
    Fallback: ``results/{scan_id}/logs/steps.log`` (legacy / no DB mirror).
    """
    try:
        from pathlib import Path
        from config.settings import settings
        
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_read(scan_dto, actor_context)

        steps_repo = get_scan_steps_repository()
        steps_raw = await steps_repo.get_steps_for_scan(scan_id)
        if steps_raw is not None and len(steps_raw) > 0:
            for step in steps_raw:
                _enrich_step_duration_fields(step)
            total_steps = len(steps_raw)
            completed_steps = sum(
                1 for s in steps_raw if s.get("status") in ("completed", "failed")
            )
            progress_percentage = int((completed_steps / total_steps * 100)) if total_steps > 0 else 0
            return {
                "scan_id": scan_id,
                "steps": steps_raw,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "progress_percentage": progress_percentage,
                "source": "database",
            }

        results_dir = Path(settings.RESULTS_DIR_HOST if hasattr(settings, 'RESULTS_DIR_HOST') else "/app/results")
        steps_log_path = results_dir / scan_id / "logs" / "steps.log"
        
        if not steps_log_path.exists():
            return {
                "scan_id": scan_id,
                "steps": [],
                "total_steps": 0,
                "completed_steps": 0,
                "progress_percentage": 0,
                "message": "Steps log file not found (scan may not have started yet)",
                "source": "file",
            }
        
        steps, total_steps, completed_steps = _read_deduplicated_steps(scan_id)
        progress_percentage = int((completed_steps / total_steps * 100)) if total_steps > 0 else 0
        
        return {
            "scan_id": scan_id,
            "steps": steps,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress_percentage": progress_percentage,
            "source": "file",
        }
        
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan steps: {str(e)}"
        )


@router.post(
    "/{scan_id}/cancel",
    response_model=ScanResponseSchema,
    summary="Cancel scan",
    description="Cancel a running or pending scan.",
    response_description="Cancelled scan information",
)
async def cancel_scan(
    scan_id: str,
    cancel_request: CancelScanSchema,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanResponseSchema:
    """
    Cancel a scan.
    
    - **scan_id**: ID of the scan to cancel
    - **cancel_request**: Cancellation parameters
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_owner(scan_dto, actor_context)

        cancel_dto = CancelScanRequestDTO(
            scan_id=scan_id,
            reason=cancel_request.reason,
            force=cancel_request.force,
            cancelled_by=actor_context.get_identifier(),
        )
        
        scan_dto = await scan_service.cancel_scan(cancel_dto)
        
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
        )
        
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{scan_id}/report-share-link",
    response_model=ReportShareLinkResponseSchema,
    summary="Get or create report share link path",
    description=(
        "Owner only. Ensures report_share_token exists in scan metadata (or regenerates it), "
        "returns the path to open the HTML report with ?share_token=."
    ),
)
async def create_report_share_link(
    scan_id: str,
    body: Optional[ReportShareLinkRequestSchema] = Body(None),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ReportShareLinkResponseSchema:
    try:
        regenerate = bool(body.regenerate) if body else False
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_owner(scan_dto, actor_context)
        meta = dict(scan_dto.metadata or {})
        tok = meta.get("report_share_token")
        need_new = (
            regenerate
            or not isinstance(tok, str)
            or len(tok.strip()) < 8
        )
        if need_new:
            new_tok = secrets.token_urlsafe(32)
            await scan_service.update_scan(
                scan_id,
                ScanUpdateRequestDTO(metadata={"report_share_token": new_tok}),
            )
            tok = new_tok
        share_path = f"/api/results/{scan_id}/report?share_token={quote(tok, safe='')}"
        return ReportShareLinkResponseSchema(share_path=share_path)
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{scan_id}/retry",
    response_model=ScanResponseSchema,
    summary="Retry failed scan",
    description="Retry a failed scan with the same configuration.",
    response_description="New scan information",
)
async def retry_scan(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> ScanResponseSchema:
    """
    Retry a failed scan.
    
    - **scan_id**: ID of the failed scan to retry
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        existing = await scan_service.get_scan_by_id(scan_id)
        _require_scan_owner(existing, actor_context)
        scan_dto = await scan_service.retry_scan(scan_id)

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
        )

    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ScanValidationException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{scan_id}/results",
    response_model=AggregatedResultSchema,
    summary="Get scan results",
    description="Get aggregated results from all scanners for a scan.",
    response_description="Aggregated scan results",
)
async def get_scan_results(
    scan_id: str,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> AggregatedResultSchema:
    """
    Get scan results.
    
    - **scan_id**: ID of the scan
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        scan_dto = await scan_service.get_scan_by_id(scan_id)
        _require_scan_read(scan_dto, actor_context)

        raise NotImplementedError("Results service not yet implemented")
        
    except ScanNotFoundException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/recent",
    response_model=List[ScanSummarySchema],
    summary="Get recent scans",
    description="Get recently created scans for the current user.",
    response_description="List of recent scan summaries",
)
async def get_recent_scans(
    limit: int = Query(10, ge=1, le=100, description="Number of scans to return"),
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> List[ScanSummarySchema]:
    """
    Get recent scans.
    
    - **limit**: Number of recent scans to return
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    try:
        if actor_context.is_authenticated:
            scan_summaries = await scan_service.get_recent_scans(
                limit, owner_user_id=actor_context.user_id
            )
        else:
            if not actor_context.session_id:
                return []
            scan_summaries = await scan_service.get_recent_scans(
                limit, guest_session_id=actor_context.session_id
            )

        return [
            ScanSummarySchema(
                id=summary.id,
                name=summary.name,
                scan_type=summary.scan_type,
                target_url=summary.target_url,
                target_type=summary.target_type,
                status=summary.status,
                created_at=summary.created_at,
                started_at=summary.started_at,
                completed_at=summary.completed_at,
                total_vulnerabilities=summary.total_vulnerabilities,
                critical_vulnerabilities=summary.critical_vulnerabilities,
                high_vulnerabilities=summary.high_vulnerabilities,
                user_id=summary.user_id,
                project_id=summary.project_id,
                tags=summary.tags,
            )
            for summary in scan_summaries
        ]

    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/batch",
    response_model=List[ScanResponseSchema],
    summary="Create batch scans",
    description="Create multiple scans with the same configuration targeting different URLs.",
    response_description="List of created scan information",
)
async def create_batch_scans(
    batch_request: BatchScanSchema,
    actor_context: ActorContext = Depends(get_actor_context),
    scan_service: ScanService = Depends(get_scan_service_dependency),
) -> List[ScanResponseSchema]:
    """
    Create batch scans.
    
    - **batch_request**: Batch scan parameters
    - **actor_context**: Resolved user/session context
    - **scan_service**: Scan service
    """
    # Bulk scan: only for logged-in users unless admin enabled guest access (BULK_SCAN_ALLOW_GUESTS)
    if not actor_context.is_authenticated:
        settings = get_settings()
        if not getattr(settings, "BULK_SCAN_ALLOW_GUESTS", False):
            raise HTTPException(
                status_code=fastapi_status.HTTP_403_FORBIDDEN,
                detail="Bulk scan is only available for logged-in users. An admin can allow guest bulk scan in Auth Settings.",
            )
    try:
        # This would typically create multiple scans in a batch
        # For now, return a placeholder
        raise NotImplementedError("Batch scan creation not yet implemented")
        
    except ScanValidationException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ScanException as e:
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.websocket("/{scan_id}/stream")
async def websocket_scan_stream(websocket: WebSocket, scan_id: str):
    """
    WebSocket endpoint for real-time scan step updates.
    
    - **scan_id**: ID of the scan to stream updates for
    """
    await websocket.accept()
    
    try:
        last_steps_hash = None
        
        while True:
            # Read and deduplicate steps
            steps, total_steps, completed_steps = _read_deduplicated_steps(scan_id)
            progress_percentage = int((completed_steps / total_steps * 100)) if total_steps > 0 else 0
            
            # Create a hash of steps to detect changes
            steps_hash = hash(json.dumps(steps, sort_keys=True))
            
            # Only send update if steps have changed
            if steps_hash != last_steps_hash:
                message = {
                    "type": "step_update",
                    "scan_id": scan_id,
                    "steps": steps,
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "progress_percentage": progress_percentage
                }
                await websocket.send_json(message)
                last_steps_hash = steps_hash
            
            # Wait 1 second before next check
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
