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
            "ALLOW_GIT_REPOS": True,
        },
        "network_intern": {
            "ALLOW_LOCAL_PATHS": True,
            "ALLOW_NETWORK_SCANS": True,
            "ALLOW_CONTAINER_REGISTRY": True,
            "ALLOW_GIT_REPOS": True,
        },
        "public_web": {
            "ALLOW_LOCAL_PATHS": False,  # Security risk
            "ALLOW_NETWORK_SCANS": True,  # Website scans allowed
            "ALLOW_CONTAINER_REGISTRY": False,  # Security risk
            "ALLOW_GIT_REPOS": True,  # Public repos OK
        },
        "enterprise": {
            "ALLOW_LOCAL_PATHS": False,  # Security risk
            "ALLOW_NETWORK_SCANS": True,  # Website scans allowed
            "ALLOW_CONTAINER_REGISTRY": True,  # Enterprise might need this
            "ALLOW_GIT_REPOS": True,
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
        
        # Network Intern: permissive + (basic or jwt)
        if security_mode == "permissive" and auth_mode in ["basic", "jwt"]:
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
            "ALLOW_GIT_REPOS": settings.ALLOW_GIT_REPOS,
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
                "SECURITY_MODE": "permissive",
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
