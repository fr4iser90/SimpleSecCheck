"""
Merge scanners table (manifest defaults in metadata) with scanner_tool_settings.

PK scanner_tool_settings.scanner_key = tools_key slug only (semgrep, sonarqube).
Uses ScannerRepository + ScannerToolSettingsRepository (DDD, no session).
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from domain.entities.scanner import Scanner
from domain.entities.scanner_tool_settings import ScannerToolSettings

logger = logging.getLogger(__name__)

_ENV_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def tools_key_from_scanner_row(sc: Scanner) -> Optional[str]:
    """Canonical key = metadata.tools_key = manifest.id only."""
    meta = sc.scanner_metadata if isinstance(sc.scanner_metadata, dict) else {}
    tk = meta.get("tools_key")
    if tk and str(tk).strip():
        return str(tk).strip()
    return None


def execution_timeout_from_meta(meta: Dict[str, Any]) -> int:
    """Only metadata.execution.timeout (synced from manifest)."""
    ex = meta.get("execution")
    if isinstance(ex, dict) and ex.get("timeout") is not None:
        try:
            t = int(ex["timeout"])
            if 30 <= t <= 86400:
                return t
        except (TypeError, ValueError):
            pass
    return 900


def build_env_from_config(config: Optional[Dict[str, Any]]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not config or not isinstance(config, dict):
        return env
    for k, v in config.items():
        if not isinstance(k, str) or not _ENV_KEY_PATTERN.match(k):
            continue
        if isinstance(v, (dict, list)):
            continue
        if v is None:
            continue
        env[k] = "true" if v is True else "false" if v is False else str(v)
    return env


def _entry(
    default_timeout: int,
    discovery_enabled: bool,
    settings_row: Optional[ScannerToolSettings],
    tools_key: str,
) -> Dict[str, Any]:
    timeout = default_timeout
    enabled = discovery_enabled
    config: Dict[str, Any] = dict(settings_row.config) if settings_row and settings_row.config else {}
    if settings_row:
        if settings_row.timeout_seconds is not None and settings_row.timeout_seconds > 0:
            timeout = int(settings_row.timeout_seconds)
        if settings_row.enabled is not None:
            enabled = bool(settings_row.enabled)
    return {
        "timeout": timeout,
        "enabled": enabled,
        "config": config,
        "env": build_env_from_config(config),
        "tools_key": tools_key,
    }


async def build_merged_tool_overrides() -> Dict[str, Dict[str, Any]]:
    """tools_key -> merged. Uses repositories (no session). Empty scanners => {}."""
    from infrastructure.container import get_scanner_repository, get_scanner_tool_settings_repository
    scanner_repo = get_scanner_repository()
    settings_repo = get_scanner_tool_settings_repository()
    scanners = await scanner_repo.list_all()
    if not scanners:
        return {}
    settings_list = await settings_repo.list_all()
    settings_map = {s.scanner_key: s for s in settings_list}
    out: Dict[str, Dict[str, Any]] = {}
    for sc in scanners:
        tk = tools_key_from_scanner_row(sc)
        if not tk:
            logger.warning(
                "Scanner %r has no metadata.tools_key (sync from manifest.id); skipping tool overrides",
                sc.name,
            )
            continue
        key = tk.strip().lower()
        meta = sc.scanner_metadata if isinstance(sc.scanner_metadata, dict) else {}
        mt = execution_timeout_from_meta(meta)
        row = settings_map.get(key)
        out[key] = _entry(mt, sc.enabled, row, key)
    return out


def overrides_map_to_json(overrides: Dict[str, Dict[str, Any]]) -> str:
    return json.dumps(overrides, separators=(",", ":"))
