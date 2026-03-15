"""
Target Type Entity

This module defines the TargetType enumeration for the backend domain.
This is the single source of truth for target types in the backend.
"""
from enum import Enum


class TargetType(str, Enum):
    """Target type enumeration - organized by category"""
    
    # Code Targets
    LOCAL_MOUNT = "local_mount"  # Local filesystem path mounted into container (dev only)
    GIT_REPO = "git_repo"  # Git repository URL cloned (dev + prod)
    UPLOADED_CODE = "uploaded_code"  # Uploaded ZIP file extracted and mounted (dev + prod)
    
    # Container Targets
    CONTAINER_REGISTRY = "container_registry"  # Container registry image (docker.io, ghcr.io, gcr.io, ECR, etc.) (dev + prod, prod: docker.io only)
    
    # Application Targets
    WEBSITE = "website"  # Website URL scanned (dev only, disabled in prod)
    API_ENDPOINT = "api_endpoint"  # REST/GraphQL API endpoint scanned (dev only, disabled in prod)
    
    # Infrastructure Targets
    NETWORK_HOST = "network_host"  # Network host/IP scanned (dev only, disabled in prod)
    KUBERNETES_CLUSTER = "kubernetes_cluster"  # Live Kubernetes cluster scanned (dev only, disabled in prod)
    
    # Mobile Targets
    APK = "apk"  # Android APK file (dev + prod)
    IPA = "ipa"  # iOS IPA file (dev + prod)
    
    # Spec Targets
    OPENAPI_SPEC = "openapi_spec"  # OpenAPI/Swagger spec file for API fuzzing (dev + prod)
    
    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all target type values as a list of strings."""
        return [target_type.value for target_type in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string value is a valid target type."""
        try:
            cls(value)
            return True
        except ValueError:
            return False
