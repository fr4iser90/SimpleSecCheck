"""
Central defaults for finding policy behavior.

Keep these values in one place to avoid duplicated literals across routes/services.
"""
from typing import Any, Dict

DEFAULT_FINDING_POLICY_PATH = ".scanning/finding-policy.json"
DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT = True


def default_scan_defaults() -> Dict[str, Any]:
    """Default scan_defaults payload stored in SystemState.config."""
    return {
        "default_finding_policy_path": DEFAULT_FINDING_POLICY_PATH,
        "finding_policy_apply_by_default": DEFAULT_FINDING_POLICY_APPLY_BY_DEFAULT,
    }
