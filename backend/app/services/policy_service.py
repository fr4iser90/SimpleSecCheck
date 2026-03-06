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
    is_staging: bool
    is_development: bool
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
    
    # Session-Konfiguration
    session_duration: int
    session_cookie_name: str
    session_header_name: str
    session_cookie_httponly: bool
    session_cookie_secure: bool
    session_cookie_samesite: str
    
    # Cookie-Konfiguration basierend auf Umgebung
    cookie_secure: bool
    cookie_samesite: str
    
    # Neue Felder für Development mit Production-Features
    force_production_policy: bool
    allow_direct_results_access: bool


def get_policy_config() -> PolicyConfig:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    force_prod_policy = os.getenv("FORCE_PRODUCTION_POLICY", "false").lower() == "true"
    
    is_prod = env == "prod"
    is_staging = env == "staging"
    is_dev = env == "dev"
    
    # UI-Features: Gestützt von FORCE_PRODUCTION_POLICY
    if force_prod_policy:
        # UI wie Production, aber ohne Session-Management
        only_git_scans = True
        allow_local_paths = False
        allow_website_scans = False
        allow_network_scans = False
        allow_bulk_scan = False
        allow_zip_upload = False
        docker_hub_only = True
        allow_direct_results_access = True  # UI-Zugriff erlauben
    elif is_prod:
        # Echte Production-Logik
        only_git_scans = True
        allow_local_paths = False
        allow_website_scans = False
        allow_network_scans = False
        allow_bulk_scan = False
        allow_zip_upload = False
        docker_hub_only = True
        allow_direct_results_access = False
    else:
        # Development/Staging
        only_git_scans = False
        allow_local_paths = True
        allow_website_scans = True
        allow_network_scans = True
        allow_bulk_scan = True
        allow_zip_upload = True
        docker_hub_only = False
        allow_direct_results_access = True
    
    # Session-Management: Nur in echtem Production
    require_sessions = is_prod
    require_queue = is_prod
    
    # Cookie-Konfiguration basierend auf Umgebung
    if is_prod:
        cookie_secure = True
        cookie_samesite = "strict"
    elif is_staging:
        cookie_secure = True  # Wie Production!
        cookie_samesite = "strict"
    else:  # dev
        cookie_secure = False
        cookie_samesite = "lax"
    
    metadata_collection = "always" if is_prod else "optional"
    
    # Session-Konfiguration
    session_duration = int(os.getenv("SESSION_DURATION", "86400"))
    session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "session_id")
    session_header_name = os.getenv("SESSION_HEADER_NAME", "X-Session-ID")
    session_cookie_httponly = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    session_cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    session_cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
    
    return PolicyConfig(
        environment=env,
        is_production=is_prod,
        is_staging=is_staging,
        is_development=is_dev,
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
        # Session-Konfiguration
        session_duration=session_duration,
        session_cookie_name=session_cookie_name,
        session_header_name=session_header_name,
        session_cookie_httponly=session_cookie_httponly,
        session_cookie_secure=session_cookie_secure,
        session_cookie_samesite=session_cookie_samesite,
        # Cookie-Konfiguration basierend auf Umgebung
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
        # Neue Felder für Development mit Production-Features
        force_production_policy=force_prod_policy,
        allow_direct_results_access=allow_direct_results_access,
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
