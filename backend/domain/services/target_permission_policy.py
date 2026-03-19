"""
Target Permission Policy

Maps target types to permissions and feature flags for the RBAC design.
See docs/RBAC_AND_PERMISSIONS_DESIGN.md.

- Feature Flags (settings): system capability (e.g. ALLOW_LOCAL_PATHS).
- Permissions: user/role capability (e.g. scan_local_path); checked when RBAC is implemented.
- Dangerous targets: require admin (or explicit permission) by default.

Local / restricted features (only on by default in Solo; off in public use cases):
- Local paths, Local containers, Network scans.
- Admin can still use these even when the use case has them disabled (admin override for self).
- In Network Intern / Enterprise, when enabled, all authenticated users can use (future: admin can grant per-user permissions).
"""
from typing import Dict, List, Set, Optional

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

# Target type -> feature flag key (in settings and feature_flags dict). One flag per target type.
# SINGLE SOURCE OF TRUTH: Add new scan-target flags here and in config.settings.Settings; rest derives from this.
FEATURE_FLAG_FOR_TARGET: Dict[str, str] = {
    "git_repo": "ALLOW_GIT_REPOS",
    "uploaded_code": "ALLOW_ZIP_UPLOAD",
    "local_mount": "ALLOW_LOCAL_PATHS",
    "container_registry": "ALLOW_REMOTE_CONTAINERS",
    "website": "ALLOW_WEBSITE_SCANS",
    "api_endpoint": "ALLOW_API_ENDPOINT_SCANS",
    "network_host": "ALLOW_NETWORK_HOST_SCANS",
    "kubernetes_cluster": "ALLOW_KUBERNETES_CLUSTER_SCANS",
    # apk, ipa, openapi_spec: no dedicated flag in current settings; treat as allowed if target type is valid
}
# All flag keys used for scan-target checks (FEATURE_FLAG_FOR_TARGET values + ALLOW_LOCAL_CONTAINERS for container local case).
ALL_SCAN_FEATURE_FLAG_KEYS: frozenset = frozenset(FEATURE_FLAG_FOR_TARGET.values()) | {"ALLOW_LOCAL_CONTAINERS"}

# Role names for RBAC (guest, user, admin). Used by role_capabilities config.
ROLE_NAMES: tuple = ("guest", "user", "admin")

# Valid target type keys for role_capabilities.allowed_target_types (backend enum values; same as TARGET_PERMISSION_MAP).
ROLE_CAPABILITY_TARGET_TYPES: frozenset = frozenset(TARGET_PERMISSION_MAP.keys())

# Human-readable labels per backend target type (public capabilities / admin UI).
TARGET_TYPE_DISPLAY_LABEL: Dict[str, str] = {
    "git_repo": "Git repos",
    "uploaded_code": "ZIP upload",
    "local_mount": "Local paths",
    "container_registry": "Remote containers",
    "website": "Website",
    "api_endpoint": "API endpoint",
    "network_host": "Network host",
    "kubernetes_cluster": "Kubernetes",
    "apk": "APK",
    "ipa": "IPA",
    "openapi_spec": "OpenAPI spec",
}

# Frontend allowed_targets keys (single source for API response shape).
_FLAG_TO_FRONTEND_KEY: Dict[str, str] = {
    "ALLOW_LOCAL_PATHS": "local_paths",
    "ALLOW_GIT_REPOS": "git_repos",
    "ALLOW_ZIP_UPLOAD": "zip_upload",
    "ALLOW_REMOTE_CONTAINERS": "container_registry",
    "ALLOW_LOCAL_CONTAINERS": "local_containers",
    "ALLOW_WEBSITE_SCANS": "website",
    "ALLOW_API_ENDPOINT_SCANS": "api_endpoint",
    "ALLOW_NETWORK_HOST_SCANS": "network_host",
    "ALLOW_KUBERNETES_CLUSTER_SCANS": "kubernetes_cluster",
}
# Display labels for "Allowed targets" help text (single source; frontend just joins this).
_FRONTEND_KEY_TO_LABEL: Dict[str, str] = {
    "local_paths": "Local paths",
    "git_repos": "Git repos",
    "zip_upload": "ZIP upload",
    "container_registry": "Remote containers",
    "local_containers": "Local containers",
    "website": "Website",
    "api_endpoint": "API endpoint",
    "network_host": "Network host",
    "kubernetes_cluster": "Kubernetes",
    "network": "Network",
}
# Order for allowed_targets_display list
_ALLOWED_TARGETS_DISPLAY_ORDER: List[str] = [
    "local_paths", "git_repos", "zip_upload", "container_registry", "local_containers", "network",
]
_NETWORK_FLAGS = frozenset({"ALLOW_WEBSITE_SCANS", "ALLOW_API_ENDPOINT_SCANS", "ALLOW_NETWORK_HOST_SCANS", "ALLOW_KUBERNETES_CLUSTER_SCANS"})

# Targets that imply host/network access or high risk. Admin-only when the feature is on; later: grant via permission.
# local_container = container_registry + local reference (localhost, 127.0.0.1, local/); checked via is_local_container_reference()
# network_host = IP/hostname scans (no separate "local_network_host" type in TargetType)
DANGEROUS_TARGETS: Set[str] = {
    "local_mount",
    "local_container",
    "network_host",
}

# Feature flags that guard "local / restricted" capabilities. Only on by default in Solo; off in Public Web.
# Admin can still scan these targets even when the flag is off (admin override for self).
LOCAL_OR_RESTRICTED_FEATURE_FLAGS: Set[str] = {
    "ALLOW_LOCAL_PATHS",
    "ALLOW_LOCAL_CONTAINERS",
    "ALLOW_WEBSITE_SCANS",
    "ALLOW_API_ENDPOINT_SCANS",
    "ALLOW_NETWORK_HOST_SCANS",
    "ALLOW_KUBERNETES_CLUSTER_SCANS",
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


def get_allow_flags_from_settings(settings: object) -> Dict[str, bool]:
    """Build allow_flags dict from settings. Single source: ALL_SCAN_FEATURE_FLAG_KEYS."""
    return {key: getattr(settings, key, True) for key in ALL_SCAN_FEATURE_FLAG_KEYS}


def get_allowed_targets_for_frontend(allow_flags: Dict[str, bool]) -> Dict[str, bool]:
    """Build allowed_targets dict for frontend config API. Single source: _FLAG_TO_FRONTEND_KEY."""
    out = {frontend_key: allow_flags.get(flag_key, True) for flag_key, frontend_key in _FLAG_TO_FRONTEND_KEY.items()}
    out["network"] = any(allow_flags.get(k, True) for k in _NETWORK_FLAGS)
    return out


def get_allowed_targets_display(allow_flags: Dict[str, bool]) -> List[str]:
    """List of human-readable labels for currently allowed targets (for UI help text). Single source: _FRONTEND_KEY_TO_LABEL."""
    allowed = get_allowed_targets_for_frontend(allow_flags)
    return [
        _FRONTEND_KEY_TO_LABEL[key]
        for key in _ALLOWED_TARGETS_DISPLAY_ORDER
        if allowed.get(key, False)
    ]


def effective_target_labels_for_role(
    allowed_target_types_for_role: List[str],
    allow_flags: Dict[str, bool],
) -> List[str]:
    """
    Human-readable target labels a role may use, intersected with instance feature flags.
    Types without a dedicated flag (e.g. apk) are included when listed for the role.
    """
    labels: List[str] = []
    seen: Set[str] = set()
    for tt in sorted(set(allowed_target_types_for_role)):
        if tt not in TARGET_PERMISSION_MAP:
            continue
        flag_key = FEATURE_FLAG_FOR_TARGET.get(tt)
        if flag_key and not allow_flags.get(flag_key, True):
            continue
        label = TARGET_TYPE_DISPLAY_LABEL.get(tt)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def check_can_scan_target(
    target_type: str,
    *,
    allow_flags: Dict[str, bool],
    is_admin: bool,
    target_url: Optional[str] = None,
) -> None:
    """
    Validate that the current actor may scan this target type.
    allow_flags: from get_allow_flags_from_settings(settings) or get_feature_flags().
    For container_registry, target_url is used to distinguish local vs remote (Docker Hub, etc.).
    Raises FeatureDisabledException if the feature flag is off.
    Raises TargetPermissionDeniedException if the target is dangerous and actor is not admin.
    """
    from domain.exceptions.scan_exceptions import FeatureDisabledException, TargetPermissionDeniedException

    flag_key = feature_flag_key_for_target(target_type)
    allowed = allow_flags.get(flag_key, True) if flag_key else True
    # Admin can use local/restricted features even when use case has them off (override for self)
    admin_can_bypass = bool(is_admin and flag_key and flag_key in LOCAL_OR_RESTRICTED_FEATURE_FLAGS)

    if flag_key == "ALLOW_LOCAL_PATHS" and not allowed and not admin_can_bypass:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_GIT_REPOS" and not allowed:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_ZIP_UPLOAD" and not allowed:
        raise FeatureDisabledException(target_type, flag_key)
    if flag_key == "ALLOW_REMOTE_CONTAINERS":
        if target_url and is_local_container_reference(target_url):
            local_ok = allow_flags.get("ALLOW_LOCAL_CONTAINERS", True)
            if not local_ok and not admin_can_bypass:
                raise FeatureDisabledException("local_container", "ALLOW_LOCAL_CONTAINERS")
            if not is_admin:
                raise TargetPermissionDeniedException(
                    "container_registry",
                    reason="Local container scanning (localhost / local registry) requires admin privileges.",
                )
        else:
            if not allowed:
                raise FeatureDisabledException(target_type, flag_key)
    if flag_key and flag_key.startswith("ALLOW_") and flag_key not in ("ALLOW_LOCAL_PATHS", "ALLOW_GIT_REPOS", "ALLOW_ZIP_UPLOAD", "ALLOW_REMOTE_CONTAINERS"):
        if not allowed and not admin_can_bypass:
            raise FeatureDisabledException(target_type, flag_key)

    if is_dangerous_target(target_type) and not is_admin:
        raise TargetPermissionDeniedException(
            target_type,
            reason="This target type requires admin privileges (e.g. local path scanning).",
        )
