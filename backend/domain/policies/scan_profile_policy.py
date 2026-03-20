"""Policy helpers for scan profile behavior and profile permissions."""
from typing import Any, Dict, Iterable, List

from domain.value_objects.scan_profile import normalize_scan_profile_name


def scan_profile_settings() -> Dict[str, Any]:
    """
    Role-based scan profile defaults and max allowed values stored in
    SystemState.config["scan_defaults"].
    """
    return {
        "scan_profile_guest": "quick",
        "scan_profile_user": "standard",
        "scan_profile_admin": "deep",
        "scan_profile_max_guest": "quick",
        "scan_profile_max_user": "standard",
        "scan_profile_max_admin": "deep",
        "scan_profile_order": ["quick", "standard", "deep"],
    }


def normalize_profile_key(value: Any) -> str:
    """Normalize a profile key to lowercase string without enforcing enum membership."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    return s


def extract_profile_catalog_from_scanner_metadata(scanners: Iterable[Any]) -> List[str]:
    """
    Build a unique profile catalog from scanner_metadata.scan_profiles keys.
    Preserves first-seen order.
    """
    out: List[str] = []
    seen = set()
    for sc in scanners:
        meta = sc.scanner_metadata if isinstance(getattr(sc, "scanner_metadata", None), dict) else {}
        sp = meta.get("scan_profiles")
        if not isinstance(sp, dict):
            continue
        for raw_name in sp.keys():
            name = normalize_profile_key(raw_name)
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(name)
    return out


def resolve_profile_order(scan_settings: Dict[str, Any], *, catalog: List[str]) -> List[str]:
    """Resolve profile order from config, constrained to catalog; fallback to catalog order."""
    raw_order = scan_settings.get("scan_profile_order")
    if not isinstance(raw_order, list) or not raw_order:
        return list(catalog)
    allowed = set(catalog)
    ordered: List[str] = []
    seen = set()
    for item in raw_order:
        key = normalize_profile_key(item)
        if key and key in allowed and key not in seen:
            seen.add(key)
            ordered.append(key)
    for c in catalog:
        if c not in seen:
            ordered.append(c)
    return ordered


def resolve_scan_profile_for_actor(
    scan_settings: Dict[str, Any],
    *,
    actor_role: str,
    is_authenticated: bool,
) -> str:
    """Resolve role-based profile from configured scan settings."""
    role = (actor_role or "").strip().lower()
    if role == "admin":
        raw = scan_settings.get("scan_profile_admin")
    elif is_authenticated:
        raw = scan_settings.get("scan_profile_user")
    else:
        raw = scan_settings.get("scan_profile_guest")
    val = normalize_profile_key(raw)
    return val or normalize_scan_profile_name(raw)


def resolve_max_allowed_scan_profile_for_actor(
    scan_settings: Dict[str, Any],
    *,
    actor_role: str,
    is_authenticated: bool,
) -> str:
    """Resolve max allowed profile for the current actor role."""
    role = (actor_role or "").strip().lower()
    if role == "admin":
        raw = scan_settings.get("scan_profile_max_admin")
    elif is_authenticated:
        raw = scan_settings.get("scan_profile_max_user")
    else:
        raw = scan_settings.get("scan_profile_max_guest")
    val = normalize_profile_key(raw)
    return val or normalize_scan_profile_name(raw)


def is_scan_profile_allowed(
    *,
    selected_profile: str,
    max_allowed_profile: str,
    profile_order: List[str],
) -> bool:
    """True if selected profile is <= max allowed profile in configured hierarchy."""
    selected = normalize_profile_key(selected_profile)
    max_allowed = normalize_profile_key(max_allowed_profile)
    order = [normalize_profile_key(p) for p in profile_order if normalize_profile_key(p)]
    if selected not in order or max_allowed not in order:
        return False
    return order.index(selected) <= order.index(max_allowed)
