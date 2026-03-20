"""
Uploads API Routes

ZIP upload for scan target type uploaded_code.
Returns upload_id to use as target_url when creating a scan with target_type=uploaded_code.
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.deps.actor_context import get_actor_context, ActorContext
from config.settings import get_settings
from application.services.upload_service import store_upload, UploadRejectedError
from domain.policies.target_permission_policy import check_can_scan_target, get_allow_flags_from_settings
from domain.entities.target_type import TargetType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


@router.post(
    "/",
    summary="Upload ZIP for code scan",
    description=(
        "Upload a ZIP file to scan as code. Returns upload_id to use as target_url "
        "when creating a scan with target_type=uploaded_code. ZIP is validated, "
        "optionally virus-scanned (ClamAV), and extracted with size/file limits."
    ),
)
async def upload_zip(
    file: UploadFile = File(..., description="ZIP file to upload"),
    actor_context: ActorContext = Depends(get_actor_context),
):
    settings = get_settings()
    if not settings.ALLOW_ZIP_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ZIP upload is disabled",
        )
    check_can_scan_target(
        TargetType.UPLOADED_CODE.value,
        allow_flags=get_allow_flags_from_settings(settings),
        is_admin=actor_context.role == "admin",
        target_url="",
    )

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive (.zip)",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            path = Path(tmp.name)
            try:
                size = 0
                max_bytes = settings.ZIP_UPLOAD_MAX_BYTES
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"ZIP too large (max {max_bytes} bytes)",
                        )
                    tmp.write(chunk)
                tmp.flush()
                upload_id = store_upload(
                    path,
                    user_id=actor_context.user_id if actor_context.is_authenticated else None,
                )
                return {"upload_id": upload_id}
            finally:
                path.unlink(missing_ok=True)
    except HTTPException:
        raise
    except UploadRejectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )
