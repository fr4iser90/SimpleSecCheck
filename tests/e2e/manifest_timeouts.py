"""
E2E: ``scan_profile``-Timeouts **nur** aus ``scanner/plugins/<id>/manifest.yaml`` — keine Test-Hardcodes.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PLUGINS = _REPO_ROOT / "scanner" / "plugins"


def _timeouts_from_manifest(data: object) -> list[int]:
    out: list[int] = []
    if not isinstance(data, dict):
        return out
    prof = data.get("scan_profiles")
    if not isinstance(prof, dict):
        return out
    for v in prof.values():
        if not isinstance(v, dict) or "timeout" not in v:
            continue
        try:
            t = int(v["timeout"])
        except (TypeError, ValueError):
            continue
        if t > 0:
            out.append(t)
    return out


def max_scan_profile_timeout_seconds_plugin(plugin_id: str) -> int:
    """Größtes ``scan_profiles.*.timeout`` für ein Plugin (z. B. ``checkov``)."""
    path = _PLUGINS / plugin_id / "manifest.yaml"
    if not path.is_file():
        return 0
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    vals = _timeouts_from_manifest(data)
    m = max(vals) if vals else 0
    if m <= 0:
        raise RuntimeError(
            f"No positive scan_profiles timeouts in scanner/plugins/{plugin_id}/manifest.yaml"
        )
    return m


def max_scan_profile_timeout_seconds_all_plugins() -> int:
    """Größtes ``scan_profiles.*.timeout`` über alle Plugin-Manifeste (ohne ``base``)."""
    m = 0
    for path in sorted(_PLUGINS.glob("*/manifest.yaml")):
        if path.parent.name == "base":
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for t in _timeouts_from_manifest(data):
            m = max(m, t)
    if m <= 0:
        raise RuntimeError(
            "No positive scan_profiles timeouts found under scanner/plugins/*/manifest.yaml"
        )
    return m
