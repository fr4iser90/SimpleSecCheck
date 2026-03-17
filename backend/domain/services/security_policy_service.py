"""
Security Policy Service

This service provides intelligent defaults for security settings based on
SECURITY_MODE and AUTH_MODE combinations, with granular feature flags as overrides.

Local / restricted features (only on by default in Solo; off in public use cases):
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
    
    # Single source: use case → SECURITY_MODE, AUTH_MODE, feature_flags. UI "✓/✗" and apply_use_case_config use this.
    USE_CASE_MAP: Dict[str, Dict[str, Any]] = {
        "solo": {
            "SECURITY_MODE": "permissive",
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
            "SECURITY_MODE": "restricted",
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
            "SECURITY_MODE": "restricted",
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
            "SECURITY_MODE": "restricted",
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
        """
        Detect use case from SECURITY_MODE and AUTH_MODE.
        
        Returns:
            Use case identifier
        """
        security_mode = settings.SECURITY_MODE.lower()
        auth_mode = settings.AUTH_MODE.lower()
        
        # Solo: permissive + free
        if security_mode == "permissive" and auth_mode == "free":
            return "solo"
        
        # Network Intern: restricted + (basic or jwt)
        if security_mode == "restricted" and auth_mode in ["basic", "jwt"]:
            return "network_intern"
        
        # Public Web: restricted + free
        if security_mode == "restricted" and auth_mode == "free":
            return "public_web"
        
        # Enterprise: restricted + jwt
        if security_mode == "restricted" and auth_mode == "jwt":
            return "enterprise"
        
        # Default: treat as solo
        return "solo"
    
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
    
    # Security mode explanations for UI (single source; no hardcoded text in frontend).
    SECURITY_MODES_EXPLAINED: Dict[str, Dict[str, Any]] = {
        "permissive": {
            "name": "Permissive",
            "description": "Allows access to host filesystem (local paths).",
            "allowed": ["Can scan local directories on the server"],
            "warning": "Only safe for single-user deployments",
        },
        "restricted": {
            "name": "Restricted",
            "description": "No access to host filesystem. Only external targets allowed.",
            "allowed": ["Allowed targets (Git, ZIP, containers, network) depend on use case — see cards below"],
            "disallowed": ["No local file paths"],
        },
    }

    @staticmethod
    def get_security_modes_explained() -> Dict[str, Dict[str, Any]]:
        """Return security mode explanations for frontend (Permissive / Restricted)."""
        return dict(SecurityPolicyService.SECURITY_MODES_EXPLAINED)

    @staticmethod
    def apply_use_case_config(use_case: str) -> Dict[str, Any]:
        """
        Get complete configuration for a use case.
        
        Args:
            use_case: Use case identifier
            
        Returns:
            Dictionary with SECURITY_MODE, AUTH_MODE, feature flags, and rate limits
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
            - security_mode: Security mode (permissive/restricted)
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
        
        def add_use_case(uid: str, name: str, description: str, security_mode: str, auth_mode: str, auth_mode_options: list) -> None:
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
                "security_mode": security_mode,
                "auth_mode": auth_mode,
                "auth_mode_options": auth_mode_options,
                "features": build_features(uid),
                "local_restricted_labels": LOCAL_RESTRICTED_FEATURE_LABELS,
                "local_restricted_on": local_restricted_on,
                "admin_can_override": True,
            }
        
        # Solo: local/restricted on by default (self-hosted only)
        add_use_case("solo", "Solo", "Single user, self-hosted. All features enabled, no restrictions.", "permissive", "free", ["free"])
        
        # Network Intern: local/restricted on so (authenticated) users can use; future: admin can grant per-user
        add_use_case("network_intern", "Network Intern", "Multiple users, internal network. User authentication required. Local/restricted features on for authenticated users.", "restricted", "basic", ["basic", "jwt"])
        
        # Public Web: local/restricted off; admin can still use for self
        add_use_case("public_web", "Public Web", "Public web access, many users. Restricted security, rate limited. Local/restricted off; admin can enable for self.", "restricted", "free", ["free"])
        
        # Enterprise: local/restricted on; future: admin can grant permissions to users
        add_use_case("enterprise", "Enterprise", "Enterprise deployment with SSO. Restricted security, JWT authentication. Local/restricted on; admin can grant permissions to users.", "restricted", "jwt", ["jwt"])
        
        return use_cases