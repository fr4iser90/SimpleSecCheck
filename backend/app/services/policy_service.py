"""
Central policy service for environment-dependent restrictions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Any

from app.services.target_service import classify_target, is_dockerhub_image_ref


@dataclass(frozen=True)
class PolicyConfig:
    environment: str
    is_production: bool
    only_git_scans: bool
    allow_local_paths: bool
    allow_website_scans: bool
    allow_network_scans: bool
    allow_bulk_scan: bool
    allow_zip_upload: bool
    require_sessions: bool
    require_queue: bool
    metadata_collection: str
    docker_hub_only: bool


def get_policy_config() -> PolicyConfig:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    is_prod = env == "prod"
    only_git_scans = os.getenv("ONLY_GIT_SCANS", "true").lower() == "true" if is_prod else False
    allow_local_paths = not is_prod
    allow_website_scans = not is_prod
    allow_network_scans = not is_prod
    allow_bulk_scan = not is_prod
    allow_zip_upload = os.getenv("ZIP_UPLOAD_ENABLED", "false").lower() == "true" if is_prod else True
    require_sessions = os.getenv("SESSION_MANAGEMENT", "true" if is_prod else "false").lower() == "true"
    require_queue = is_prod
    metadata_collection = "always" if is_prod else "optional"
    docker_hub_only = is_prod
    return PolicyConfig(
        environment=env,
        is_production=is_prod,
        only_git_scans=only_git_scans,
        allow_local_paths=allow_local_paths,
        allow_website_scans=allow_website_scans,
        allow_network_scans=allow_network_scans,
        allow_bulk_scan=allow_bulk_scan,
        allow_zip_upload=allow_zip_upload,
        require_sessions=require_sessions,
        require_queue=require_queue,
        metadata_collection=metadata_collection,
        docker_hub_only=docker_hub_only,
    )


def get_ui_features() -> Dict[str, Any]:
    policy = get_policy_config()
    return {
        "scan_types": {
            "code": True,
            "image": True,
            "website": policy.allow_website_scans,
            "network": policy.allow_network_scans,
        },
        "bulk_scan": policy.allow_bulk_scan,
        "local_paths": policy.allow_local_paths,
        "git_only": policy.only_git_scans,
        "queue_enabled": policy.require_queue,
        "session_management": policy.require_sessions,
        "metadata_collection": policy.metadata_collection,
        "auto_shutdown": not policy.is_production,
        "zip_upload": policy.allow_zip_upload,
        "owasp_auto_update_enabled": os.getenv("OWASP_AUTO_UPDATE_ENABLED", "true" if policy.is_production else "false").lower() == "true",
    }


def validate_scan_request(scan_type: str, target: str) -> None:
    policy = get_policy_config()
    target_info = classify_target(scan_type, target)

    if policy.is_production:
        if policy.only_git_scans and scan_type not in {"code", "image"}:
            raise ValueError(
                f"Only Git scans (code type) or image scans are allowed in production mode. Requested type: {scan_type}"
            )

        if scan_type == "code" and target_info.is_local_path and not policy.allow_local_paths:
            raise ValueError("Only Git repository URLs or Docker images are allowed in production mode")

        if scan_type == "code" and target_info.is_image and policy.docker_hub_only and not is_dockerhub_image_ref(target):
            raise ValueError("Production Mode: Only Docker Hub images are allowed (use docker.io/... or unqualified image names).")

        if scan_type == "image" and policy.docker_hub_only and not is_dockerhub_image_ref(target):
            raise ValueError("Only Docker images are allowed for image scans")


def is_session_required() -> bool:
    return get_policy_config().require_sessions


def is_queue_required() -> bool:
    return get_policy_config().require_queue
