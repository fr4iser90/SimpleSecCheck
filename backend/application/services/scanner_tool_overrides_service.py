"""
Merge scanners table (manifest defaults in metadata) with scanner_tool_settings.

PK scanner_tool_settings.scanner_key = tools_key slug only (semgrep, sonarqube).
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Scanner, ScannerToolSettings

logger = logging.getLogger(__name__)

_ENV_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def tools_key_from_scanner_row(sc: Scanner) -> Optional[str]:
    """Canonical key = metadata.tools_key = manifest.id only. No slugify, no name fallback."""
    meta = sc.scanner_metadata if isinstance(sc.scanner_metadata, dict) else {}
    tk = meta.get("tools_key")
    if tk and str(tk).strip():
        return str(tk).strip()
    return None


def execution_timeout_from_meta(meta: Dict[str, Any]) -> int:
    """Only metadata.execution.timeout (synced from manifest). No other keys."""
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
    db_row: Optional[ScannerToolSettings],
    tools_key: str,
) -> Dict[str, Any]:
    timeout = default_timeout
    enabled = discovery_enabled
    config: Dict[str, Any] = dict(db_row.config) if db_row and db_row.config else {}
    if db_row:
        if db_row.timeout_seconds is not None and db_row.timeout_seconds > 0:
            timeout = int(db_row.timeout_seconds)
        if db_row.enabled is not None:
            enabled = bool(db_row.enabled)
    return {
        "timeout": timeout,
        "enabled": enabled,
        "config": config,
        "env": build_env_from_config(config),
        "tools_key": tools_key,
    }


async def build_merged_tool_overrides(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """tools_key -> merged. Empty scanners table => {} (no error)."""
    result = await session.execute(select(Scanner))
    scanners = list(result.scalars().all())
    if not scanners:
        return {}

    result2 = await session.execute(select(ScannerToolSettings))
    settings_map = {r.scanner_key: r for r in result2.scalars().all()}

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


async def find_scanner_by_tools_key(session: AsyncSession, tools_key: str) -> Optional[Scanner]:
    """Resolve admin URL segment to Scanner row."""
    want = (tools_key or "").strip().lower()
    if not want:
        return None
    result = await session.execute(select(Scanner))
    for sc in result.scalars().all():
        tk = tools_key_from_scanner_row(sc)
        if tk and tk.strip().lower() == want:
            return sc
    return None
