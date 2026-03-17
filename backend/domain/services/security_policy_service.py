"""
Security Policy Service

Use case + feature flags. No security mode; use case determines AUTH_MODE and feature flag defaults.

Feature flags (only on by default in Solo; off in public use cases):
- Local paths, Local containers, Network scans.
- In Public Web these are OFF; admin can still use them (admin override for self).
- In Network Intern / Enterprise they can be ON so (authenticated) users can use them;
  future: admin can grant per-user permissions (e.g. allow user X to run network scans).
"""
from typing import Dict, Any, List
from enum import Enum

from config.settings import settings
from domain.services.target_permission_policy import get_allow_flags_from_settings


class UseCase(str, Enum):
    """Deployment use cases."""
    SOLO = "solo"  # Single user, self-hosted
    NETWORK_INTERN = "network_intern"  # Multiple users, internal network
    PUBLIC_WEB = "public_web"  # Public web, many users
    ENTERPRISE = "enterprise"  # Enterprise with SSO


# Local/restricted feature labels (only on by default in Solo; admin can override when off)
LOCAL_RESTRICTED_FEATURE_LABELS: List[str] = [
    "Local paths",
    "Local containers",
    "Network scans",
]


class SecurityPolicyService:
    """Service for managing security policies and feature flags."""
    
    # Single source: use case → AUTH_MODE, feature_flags.
    USE_CASE_MAP: Dict[str, Dict[str, Any]] = {
        "solo": {
            "AUTH_MODE": "free",
            "feature_flags": {
                "ALLOW_LOCAL_PATHS": True,
                "ALLOW_WEBSITE_SCANS": True,
                "ALLOW_API_ENDPOINT_SCANS": True,
                "ALLOW_NETWORK_HOST_SCANS": True,
                "ALLOW_KUBERNETES_CLUSTER_SCANS": True,
                "ALLOW_REMOTE_CONTAINERS": True,
                "ALLOW_LOCAL_CONTAINERS": True,
                "ALLOW_GIT_REPOS": True,
                "ALLOW_ZIP_UPLOAD": True,
            },
        },
        "network_intern": {
            "AUTH_MODE": "basic",
            "feature_flags": {
                "ALLOW_LOCAL_PATHS": False,
                "ALLOW_WEBSITE_SCANS": True,
                "ALLOW_API_ENDPOINT_SCANS": True,
                "ALLOW_NETWORK_HOST_SCANS": True,
                "ALLOW_KUBERNETES_CLUSTER_SCANS": True,
                "ALLOW_REMOTE_CONTAINERS": True,
                "ALLOW_LOCAL_CONTAINERS": True,
                "ALLOW_GIT_REPOS": True,
                "ALLOW_ZIP_UPLOAD": True,
            },
        },
        "public_web": {
            "AUTH_MODE": "free",
            "feature_flags": {
                "ALLOW_LOCAL_PATHS": False,
                "ALLOW_WEBSITE_SCANS": False,
                "ALLOW_API_ENDPOINT_SCANS": False,
                "ALLOW_NETWORK_HOST_SCANS": False,
                "ALLOW_KUBERNETES_CLUSTER_SCANS": False,
                "ALLOW_REMOTE_CONTAINERS": False,
                "ALLOW_LOCAL_CONTAINERS": False,
                "ALLOW_GIT_REPOS": True,
                "ALLOW_ZIP_UPLOAD": True,
            },
        },
        "enterprise": {
            "AUTH_MODE": "jwt",
            "feature_flags": {
                "ALLOW_LOCAL_PATHS": False,
                "ALLOW_WEBSITE_SCANS": True,
                "ALLOW_API_ENDPOINT_SCANS": True,
                "ALLOW_NETWORK_HOST_SCANS": True,
                "ALLOW_KUBERNETES_CLUSTER_SCANS": True,
                "ALLOW_REMOTE_CONTAINERS": True,
                "ALLOW_LOCAL_CONTAINERS": True,
                "ALLOW_GIT_REPOS": True,
                "ALLOW_ZIP_UPLOAD": True,
            },
        },
    }
    
    # Rate limits per use case and user type
    RATE_LIMITS: Dict[str, Dict[str, Dict[str, int]]] = {
        "solo": {
            "guest": {"requests": 5000, "window": 3600},
            "authenticated": {"requests": 5000, "window": 3600},
            "admin": {"requests": 5000, "window": 3600},
        },
        "network_intern": {
            "guest": {"requests": 100, "window": 3600},
            "authenticated": {"requests": 1000, "window": 3600},
            "admin": {"requests": 5000, "window": 3600},
        },
        "public_web": {
            "guest": {"requests": 100, "window": 3600},
            "authenticated": {"requests": 500, "window": 3600},
            "admin": {"requests": 2000, "window": 3600},
        },
        "enterprise": {
            "guest": {"requests": 50, "window": 3600},
            "authenticated": {"requests": 1000, "window": 3600},
            "admin": {"requests": 5000, "window": 3600},
        },
    }
    
    @staticmethod
    def detect_use_case() -> str:
        """Return current use case from settings (solo|network_intern|public_web|enterprise)."""
        return getattr(settings, "USE_CASE", "solo") or "solo"
    
    @staticmethod
    def get_rate_limits(use_case: str = None) -> Dict[str, Dict[str, int]]:
        """
        Get rate limits for the current configuration.
        
        Args:
            use_case: Optional use case override
            
        Returns:
            Dictionary of rate limits per user type
        """
        if use_case is None:
            use_case = SecurityPolicyService.detect_use_case()
        
        return SecurityPolicyService.RATE_LIMITS.get(use_case, SecurityPolicyService.RATE_LIMITS["solo"])
    
    @staticmethod
    def get_feature_flags(use_case: str = None) -> Dict[str, bool]:
        """
        Get feature flag defaults for the current configuration.
        
        Args:
            use_case: Optional use case override
            
        Returns:
            Dictionary of feature flags
        """
        if use_case is None:
            use_case = SecurityPolicyService.detect_use_case()
        
        # Return current settings (single source: get_allow_flags_from_settings uses ALL_SCAN_FEATURE_FLAG_KEYS)
        return get_allow_flags_from_settings(settings)
    
    @staticmethod
    def apply_use_case_config(use_case: str) -> Dict[str, Any]:
        """
        Get complete configuration for a use case.
        
        Args:
            use_case: Use case identifier
            
        Returns:
            Dictionary with AUTH_MODE, feature flags, and rate limits
        """
        entry = SecurityPolicyService.USE_CASE_MAP.get(use_case, SecurityPolicyService.USE_CASE_MAP["solo"])
        config = dict(entry)
        config["rate_limits"] = SecurityPolicyService.RATE_LIMITS.get(use_case, SecurityPolicyService.RATE_LIMITS["solo"])
        return config
    
    @staticmethod
    def get_all_use_cases() -> Dict[str, Dict[str, Any]]:
        """
        Get all available use cases with metadata for frontend display.
        
        Returns:
            Dictionary mapping use case IDs to their metadata including:
            - id: Use case identifier
            - name: Display name
            - description: Short description
            - auth_mode: Authentication mode (free/basic/jwt)
            - auth_mode_options: Available auth mode options for this use case
            - features: List of enabled/disabled features with descriptions
        """
        use_cases = {}
        
        # Helper to build feature descriptions
        def build_features(use_case_id: str) -> list:
            features = []
            flags = SecurityPolicyService.USE_CASE_MAP.get(use_case_id, SecurityPolicyService.USE_CASE_MAP["solo"]).get("feature_flags", {})
            
            if flags.get("ALLOW_LOCAL_PATHS", False):
                features.append({"type": "allowed", "text": "Local paths allowed"})
            else:
                features.append({"type": "disabled", "text": "Local paths disabled"})
            
            allowed = []
            if flags.get("ALLOW_GIT_REPOS", False):
                allowed.append("Git repos")
            if flags.get("ALLOW_REMOTE_CONTAINERS", False):
                allowed.append("Remote containers")
            if flags.get("ALLOW_LOCAL_CONTAINERS", False):
                allowed.append("Local containers")
            if flags.get("ALLOW_WEBSITE_SCANS", False):
                allowed.append("Website")
            if flags.get("ALLOW_API_ENDPOINT_SCANS", False):
                allowed.append("API endpoint")
            if flags.get("ALLOW_NETWORK_HOST_SCANS", False):
                allowed.append("Network host")
            if flags.get("ALLOW_KUBERNETES_CLUSTER_SCANS", False):
                allowed.append("Kubernetes")
            if flags.get("ALLOW_ZIP_UPLOAD", False):
                allowed.append("ZIP upload")
            
            if allowed:
                features.append({"type": "allowed", "text": ", ".join(allowed)})
            # When local/restricted are off, note that admin can still use them
            network_any = (
                flags.get("ALLOW_WEBSITE_SCANS", False)
                or flags.get("ALLOW_API_ENDPOINT_SCANS", False)
                or flags.get("ALLOW_NETWORK_HOST_SCANS", False)
                or flags.get("ALLOW_KUBERNETES_CLUSTER_SCANS", False)
            )
            local_on = (
                flags.get("ALLOW_LOCAL_PATHS", False)
                or flags.get("ALLOW_LOCAL_CONTAINERS", False)
                or network_any
            )
            if not local_on:
                features.append({
                    "type": "info",
                    "text": "Local/restricted (paths, local containers, network) off — admin can enable for self",
                })
            return features
        
        def add_use_case(uid: str, name: str, description: str, auth_mode: str, auth_mode_options: list) -> None:
            flags = SecurityPolicyService.USE_CASE_MAP.get(uid, SecurityPolicyService.USE_CASE_MAP["solo"]).get("feature_flags", {})
            network_any = (
                flags.get("ALLOW_WEBSITE_SCANS", False)
                or flags.get("ALLOW_API_ENDPOINT_SCANS", False)
                or flags.get("ALLOW_NETWORK_HOST_SCANS", False)
                or flags.get("ALLOW_KUBERNETES_CLUSTER_SCANS", False)
            )
            local_restricted_on = (
                flags.get("ALLOW_LOCAL_PATHS", False)
                or flags.get("ALLOW_LOCAL_CONTAINERS", False)
                or network_any
            )
            use_cases[uid] = {
                "id": uid,
                "name": name,
                "description": description,
                "auth_mode": auth_mode,
                "auth_mode_options": auth_mode_options,
                "features": build_features(uid),
                "local_restricted_labels": LOCAL_RESTRICTED_FEATURE_LABELS,
                "local_restricted_on": local_restricted_on,
                "admin_can_override": True,
            }
        
        add_use_case("solo", "Solo", "Single user, self-hosted. All features enabled, no restrictions.", "free", ["free"])
        add_use_case("network_intern", "Network Intern", "Multiple users, internal network. User authentication required. Local/restricted features on for authenticated users.", "basic", ["basic", "jwt"])
        add_use_case("public_web", "Public Web", "Public web access, many users. Rate limited. Local/restricted off; admin can enable for self.", "free", ["free"])
        add_use_case("enterprise", "Enterprise", "Enterprise deployment with SSO. JWT authentication. Local/restricted on; admin can grant permissions to users.", "jwt", ["jwt"])
        
        return use_cases