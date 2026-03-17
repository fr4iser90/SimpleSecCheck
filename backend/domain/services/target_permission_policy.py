"""
Target Permission Policy

Maps target types to permissions and feature flags for the RBAC design.
See docs/RBAC_AND_PERMISSIONS_DESIGN.md.

- Feature Flags (settings): system capability (e.g. ALLOW_LOCAL_PATHS).
- Permissions: user/role capability (e.g. scan_local_path); checked when RBAC is implemented.
- Dangerous targets: require admin (or explicit permission) by default.
"""
from typing import Dict, Set, Optional

# -----------------------------------------------------------------------------
# Permission names (for RBAC: one per controllable target type)
# Naming: scan_<target_type> with optional alias (e.g. local_mount -> scan_local_path)
# -----------------------------------------------------------------------------

PERMISSION_SCAN_GIT_REPO = "scan_git_repo"
PERMISSION_SCAN_ZIP_UPLOAD = "scan_zip_upload"
PERMISSION_SCAN_LOCAL_PATH = "scan_local_path"
PERMISSION_SCAN_CONTAINER_REGISTRY = "scan_container_registry"
PERMISSION_SCAN_WEBSITE = "scan_website"
PERMISSION_SCAN_API_ENDPOINT = "scan_api_endpoint"
PERMISSION_SCAN_NETWORK_TARGET = "scan_network_target"
PERMISSION_SCAN_KUBERNETES_CLUSTER = "scan_kubernetes_cluster"
PERMISSION_SCAN_APK = "scan_apk"
PERMISSION_SCAN_IPA = "scan_ipa"
PERMISSION_SCAN_OPENAPI_SPEC = "scan_openapi_spec"

ALL_SCAN_PERMISSIONS: Set[str] = {
    PERMISSION_SCAN_GIT_REPO,
    PERMISSION_SCAN_ZIP_UPLOAD,
    PERMISSION_SCAN_LOCAL_PATH,
    PERMISSION_SCAN_CONTAINER_REGISTRY,
    PERMISSION_SCAN_WEBSITE,
    PERMISSION_SCAN_API_ENDPOINT,
    PERMISSION_SCAN_NETWORK_TARGET,
    PERMISSION_SCAN_KUBERNETES_CLUSTER,
    PERMISSION_SCAN_APK,
    PERMISSION_SCAN_IPA,
    PERMISSION_SCAN_OPENAPI_SPEC,
}

# Target type (value from TargetType enum) -> permission name
TARGET_PERMISSION_MAP: Dict[str, str] = {
    "git_repo": PERMISSION_SCAN_GIT_REPO,
    "uploaded_code": PERMISSION_SCAN_ZIP_UPLOAD,
    "local_mount": PERMISSION_SCAN_LOCAL_PATH,
    "container_registry": PERMISSION_SCAN_CONTAINER_REGISTRY,
    "website": PERMISSION_SCAN_WEBSITE,
    "api_endpoint": PERMISSION_SCAN_API_ENDPOINT,
    "network_host": PERMISSION_SCAN_NETWORK_TARGET,
    "kubernetes_cluster": PERMISSION_SCAN_KUBERNETES_CLUSTER,
    "apk": PERMISSION_SCAN_APK,
    "ipa": PERMISSION_SCAN_IPA,
    "openapi_spec": PERMISSION_SCAN_OPENAPI_SPEC,
}

# Target type -> feature flag key (in settings and feature_flags dict)
FEATURE_FLAG_FOR_TARGET: Dict[str, str] = {
    "git_repo": "ALLOW_GIT_REPOS",
    "uploaded_code": "ALLOW_ZIP_UPLOAD",
    "local_mount": "ALLOW_LOCAL_PATHS",
    "container_registry": "ALLOW_CONTAINER_REGISTRY",
    "website": "ALLOW_NETWORK_SCANS",
    "api_endpoint": "ALLOW_NETWORK_SCANS",
    "network_host": "ALLOW_NETWORK_SCANS",
    "kubernetes_cluster": "ALLOW_NETWORK_SCANS",
    # apk, ipa, openapi_spec: no dedicated flag in current settings; treat as allowed if target type is valid
}

# Targets that imply host/network access or high risk. Default: admin-only when RBAC is enforced.
# local_container = container_registry + local reference (localhost, 127.0.0.1, local/); checked via is_local_container_reference()
DANGEROUS_TARGETS: Set[str] = {
    "local_mount",
    "local_container",
}

# Image reference is considered "local" (local Docker or local registry) if host is localhost/127.0.0.1 or prefix "local/"
def is_local_container_reference(target_url: str) -> bool:
    """True if the container image reference points to local Docker or a local registry."""
    if not target_url or not target_url.strip():
        return False
    s = target_url.strip().lower()
    if s.startswith("local/"):
        return True
    if s.startswith("localhost/") or s.startswith("localhost:"):
        return True
    if s.startswith("127.0.0.1/") or s.startswith("127.0.0.1:"):
        return True
    return False

# Optional: security level for UI/policy (safe | restricted | dangerous)
TARGET_SECURITY_LEVEL: Dict[str, str] = {
    "git_repo": "safe",
    "uploaded_code": "safe",
    "container_registry": "restricted",
    "website": "restricted",
    "api_endpoint": "restricted",
    "network_host": "restricted",
    "kubernetes_cluster": "restricted",
    "local_mount": "dangerous",
    "apk": "safe",
    "ipa": "safe",
    "openapi_spec": "safe",
}


def permission_for_target(target_type: str) -> Optional[str]:
    """Return the permission name required to scan this target type, or None if unknown."""
    return TARGET_PERMISSION_MAP.get(target_type)


def is_dangerous_target(target_type: str) -> bool:
    """Return True if this target type is considered dangerous (e.g. local_mount)."""
    return target_type in DANGEROUS_TARGETS


def feature_flag_key_for_target(target_type: str) -> Optional[str]:
    """Return the feature flag key (e.g. ALLOW_LOCAL_PATHS) for this target type, or None."""
    return FEATURE_FLAG_FOR_TARGET.get(target_type)


def security_level_for_target(target_type: str) -> str:
    """Return security level: safe, restricted, or dangerous. Default safe."""
    return TARGET_SECURITY_LEVEL.get(target_type, "safe")


def check_can_scan_target(
    target_type: str,
    *,
    allow_local_paths: bool,
    allow_git_repos: bool,
    allow_zip_upload: bool,
    allow_container_registry: bool,
    allow_local_containers: bool,
    allow_network_scans: bool,
    is_admin: bool,
    target_url: Optional[str] = None,
) -> None:
    """
    Validate that the current actor may scan this target type.
    For container_registry, target_url is used to distinguish local vs remote (Docker Hub, etc.).
    Raises FeatureDisabledException if the feature flag is off.
    Raises TargetPermissionDeniedException if the target is dangerous and actor is not admin.
    """
    from domain.exceptions.scan_exceptions import FeatureDisabledException, TargetPermissionDeniedException

    flag_key = feature_flag_key_for_target(target_type)
    if flag_key == "ALLOW_LOCAL_PATHS" and not allow_local_paths:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_GIT_REPOS" and not allow_git_repos:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_ZIP_UPLOAD" and not allow_zip_upload:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_CONTAINER_REGISTRY":
        if target_url and is_local_container_reference(target_url):
            if not allow_local_containers:
                raise FeatureDisabledException("local_container", "ALLOW_LOCAL_CONTAINERS")
            if not is_admin:
                raise TargetPermissionDeniedException(
                    "container_registry",
                    reason="Local container scanning (localhost / local registry) requires admin privileges.",
                )
        else:
            if not allow_container_registry:
                raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_NETWORK_SCANS" and not allow_network_scans:
        raise FeatureDisabledException(target_type, flag_key)

    if is_dangerous_target(target_type) and not is_admin:
        raise TargetPermissionDeniedException(
            target_type,
            reason="This target type requires admin privileges (e.g. local path scanning).",
        )
