"""
Security Policy Service

This service provides intelligent defaults for security settings based on
SECURITY_MODE and AUTH_MODE combinations, with granular feature flags as overrides.
"""
from typing import Dict, Any
from enum import Enum

from config.settings import settings


class UseCase(str, Enum):
    """Deployment use cases."""
    SOLO = "solo"  # Single user, self-hosted
    NETWORK_INTERN = "network_intern"  # Multiple users, internal network
    PUBLIC_WEB = "public_web"  # Public web, many users
    ENTERPRISE = "enterprise"  # Enterprise with SSO


class SecurityPolicyService:
    """Service for managing security policies and feature flags."""
    
    # Rate limits per use case and user type
    RATE_LIMITS: Dict[str, Dict[str, Dict[str, int]]] = {
        "solo": {
            "guest": {"requests": 5000, "window": 3600},  # 5000 req/h
            "authenticated": {"requests": 5000, "window": 3600},
            "admin": {"requests": 5000, "window": 3600},
        },
        "network_intern": {
            "guest": {"requests": 100, "window": 3600},  # 100 req/h for guests
            "authenticated": {"requests": 1000, "window": 3600},  # 1000 req/h per user
            "admin": {"requests": 5000, "window": 3600},
        },
        "public_web": {
            "guest": {"requests": 100, "window": 3600},  # 100 req/h for guests
            "authenticated": {"requests": 500, "window": 3600},  # 500 req/h per user
            "admin": {"requests": 2000, "window": 3600},
        },
        "enterprise": {
            "guest": {"requests": 50, "window": 3600},  # 50 req/h for guests
            "authenticated": {"requests": 1000, "window": 3600},  # 1000 req/h per user
            "admin": {"requests": 5000, "window": 3600},
        },
    }
    
    # Feature flag defaults per use case
    FEATURE_DEFAULTS: Dict[str, Dict[str, bool]] = {
        "solo": {
            "ALLOW_LOCAL_PATHS": True,
            "ALLOW_NETWORK_SCANS": True,
            "ALLOW_CONTAINER_REGISTRY": True,
            "ALLOW_LOCAL_CONTAINERS": True,
            "ALLOW_GIT_REPOS": True,
            "ALLOW_ZIP_UPLOAD": True,
        },
        "network_intern": {
            "ALLOW_LOCAL_PATHS": False,  # Security: No host filesystem access for multiple users
            "ALLOW_NETWORK_SCANS": True,  # External network scans allowed
            "ALLOW_CONTAINER_REGISTRY": True,
            "ALLOW_LOCAL_CONTAINERS": True,
            "ALLOW_GIT_REPOS": True,
            "ALLOW_ZIP_UPLOAD": True,
        },
        "public_web": {
            "ALLOW_LOCAL_PATHS": False,  # Security risk
            "ALLOW_NETWORK_SCANS": True,  # Website scans allowed
            "ALLOW_CONTAINER_REGISTRY": False,  # Security risk (remote registries)
            "ALLOW_LOCAL_CONTAINERS": False,  # Security risk; enable for admin homelab only
            "ALLOW_GIT_REPOS": True,  # Public repos OK
            "ALLOW_ZIP_UPLOAD": True,
        },
        "enterprise": {
            "ALLOW_LOCAL_PATHS": False,  # Security risk
            "ALLOW_NETWORK_SCANS": True,  # Website scans allowed
            "ALLOW_CONTAINER_REGISTRY": True,  # Enterprise might need this
            "ALLOW_LOCAL_CONTAINERS": True,  # Admin can scan local registries
            "ALLOW_GIT_REPOS": True,
            "ALLOW_ZIP_UPLOAD": True,
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
        
        defaults = SecurityPolicyService.FEATURE_DEFAULTS.get(use_case, SecurityPolicyService.FEATURE_DEFAULTS["solo"])
        
        # Use explicit settings (no fallbacks)
        return {
            "ALLOW_LOCAL_PATHS": settings.ALLOW_LOCAL_PATHS,
            "ALLOW_NETWORK_SCANS": settings.ALLOW_NETWORK_SCANS,
            "ALLOW_CONTAINER_REGISTRY": settings.ALLOW_CONTAINER_REGISTRY,
            "ALLOW_LOCAL_CONTAINERS": getattr(settings, "ALLOW_LOCAL_CONTAINERS", True),
            "ALLOW_GIT_REPOS": settings.ALLOW_GIT_REPOS,
            "ALLOW_ZIP_UPLOAD": settings.ALLOW_ZIP_UPLOAD,
        }
    
    @staticmethod
    def apply_use_case_config(use_case: str) -> Dict[str, Any]:
        """
        Get complete configuration for a use case.
        
        Args:
            use_case: Use case identifier
            
        Returns:
            Dictionary with SECURITY_MODE, AUTH_MODE, feature flags, and rate limits
        """
        use_case_map = {
            "solo": {
                "SECURITY_MODE": "permissive",
                "AUTH_MODE": "free",
            },
            "network_intern": {
                "SECURITY_MODE": "restricted",  # No host filesystem access for security
                "AUTH_MODE": "basic",  # Default to basic, can be changed to jwt
            },
            "public_web": {
                "SECURITY_MODE": "restricted",
                "AUTH_MODE": "free",
            },
            "enterprise": {
                "SECURITY_MODE": "restricted",
                "AUTH_MODE": "jwt",
            },
        }
        
        config = use_case_map.get(use_case, use_case_map["solo"])
        config["feature_flags"] = SecurityPolicyService.FEATURE_DEFAULTS.get(use_case, SecurityPolicyService.FEATURE_DEFAULTS["solo"])
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
            flags = SecurityPolicyService.FEATURE_DEFAULTS.get(use_case_id, {})
            
            if flags.get("ALLOW_LOCAL_PATHS", False):
                features.append({"type": "allowed", "text": "Local paths allowed"})
            else:
                features.append({"type": "disabled", "text": "Local paths disabled"})
            
            allowed = []
            if flags.get("ALLOW_GIT_REPOS", False):
                allowed.append("Git repos")
            if flags.get("ALLOW_CONTAINER_REGISTRY", False):
                allowed.append("containers")
            if flags.get("ALLOW_NETWORK_SCANS", False):
                allowed.append("network scans")
            if flags.get("ALLOW_ZIP_UPLOAD", False):
                allowed.append("ZIP upload")
            
            if allowed:
                features.append({"type": "allowed", "text": ", ".join(allowed)})
            
            return features
        
        # Solo
        use_cases["solo"] = {
            "id": "solo",
            "name": "Solo",
            "description": "Single user, self-hosted. All features enabled, no restrictions.",
            "security_mode": "permissive",
            "auth_mode": "free",
            "auth_mode_options": ["free"],
            "features": build_features("solo"),
        }
        
        # Network Intern
        use_cases["network_intern"] = {
            "id": "network_intern",
            "name": "Network Intern",
            "description": "Multiple users, internal network. User authentication required.",
            "security_mode": "restricted",
            "auth_mode": "basic",
            "auth_mode_options": ["basic", "jwt"],
            "features": build_features("network_intern"),
        }
        
        # Public Web
        use_cases["public_web"] = {
            "id": "public_web",
            "name": "Public Web",
            "description": "Public web access, many users. Restricted security, rate limited.",
            "security_mode": "restricted",
            "auth_mode": "free",
            "auth_mode_options": ["free"],
            "features": build_features("public_web"),
        }
        
        # Enterprise
        use_cases["enterprise"] = {
            "id": "enterprise",
            "name": "Enterprise",
            "description": "Enterprise deployment with SSO. Restricted security, JWT authentication.",
            "security_mode": "restricted",
            "auth_mode": "jwt",
            "auth_mode_options": ["jwt"],
            "features": build_features("enterprise"),
        }
        
        return use_cases