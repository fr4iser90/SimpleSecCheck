"""
Merge stored role_capabilities from SystemState.config with defaults.
Used by admin API and public capabilities snapshot.
"""
from typing import Any, Dict, List, Optional

from domain.services.target_permission_policy import ROLE_CAPABILITY_TARGET_TYPES, ROLE_NAMES


def default_role_capabilities() -> Dict[str, Any]:
    """Default role_capabilities when none stored."""
    all_targets = list(ROLE_CAPABILITY_TARGET_TYPES)
    return {
        "guest": {
            "allowed_target_types": ["git_repo", "uploaded_code"],
            "allowed_scanner_tools_keys": [],
            "my_targets_allowed": False,
            "my_targets_target_types": None,
        },
        "user": {
            "allowed_target_types": all_targets,
            "allowed_scanner_tools_keys": [],
            "my_targets_allowed": True,
            "my_targets_target_types": None,
        },
        "admin": {
            "allowed_target_types": all_targets,
            "allowed_scanner_tools_keys": [],
            "my_targets_allowed": True,
            "my_targets_target_types": None,
        },
    }


def merge_role_capabilities_raw(config: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Return merged guest/user/admin capability dicts (plain dicts, not Pydantic).
    """
    raw = (config or {}).get("role_capabilities") or {}
    if not isinstance(raw, dict):
        raw = {}
    defaults = default_role_capabilities()
    out: Dict[str, Dict[str, Any]] = {}
    for role in ROLE_NAMES:
        merged = {**(defaults.get(role) or {}), **(raw.get(role) or {})}
        out[role] = {
            "allowed_target_types": list(merged.get("allowed_target_types") or []),
            "allowed_scanner_tools_keys": list(merged.get("allowed_scanner_tools_keys") or []),
            "my_targets_allowed": bool(merged.get("my_targets_allowed", False)),
            "my_targets_target_types": merged.get("my_targets_target_types"),
        }
    return out
