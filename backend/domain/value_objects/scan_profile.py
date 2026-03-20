"""
User-facing scan profiles (quick / standard / deep).

Tool-specific defaults live only in each plugin's manifest.yaml under `scan_profiles`.
This module holds shared types and tuning merge only — no per-tool env literals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ScanProfileName(str, Enum):
    """Public scan profile — one knob for users; tools map it via manifest."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


@dataclass(frozen=True)
class ResolvedScanProfile:
    """Resolved profile after optional per-tool tuning (hints from manifest when present)."""

    profile: str
    depth: str
    intensity: str
    coverage: str
    per_tool: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "depth": self.depth,
            "intensity": self.intensity,
            "coverage": self.coverage,
            "per_tool": self.per_tool,
        }


def normalize_scan_profile_name(name: Optional[str]) -> str:
    if not name or not str(name).strip():
        return ScanProfileName.STANDARD.value
    s = str(name).strip().lower()
    if s not in {e.value for e in ScanProfileName}:
        return ScanProfileName.STANDARD.value
    return s


def default_scan_profile_for_role(actor_role: Optional[str], *, is_authenticated: bool) -> str:
    """
    Role-based default scan profile.

    admin -> deep, authenticated user -> standard, guest -> quick.
    """
    role = (actor_role or "").strip().lower()
    if role == "admin":
        return ScanProfileName.DEEP.value
    if is_authenticated:
        return ScanProfileName.STANDARD.value
    return ScanProfileName.QUICK.value


def merge_profile_tuning(
    base: ResolvedScanProfile,
    profile_tuning: Optional[Dict[str, Any]],
) -> ResolvedScanProfile:
    """
    Deep-merge optional tuning into per_tool env.

    Tuning shape: { "zap": { "ZAP_OPTIONS": "...", "ZAP_USE_ACTIVE_SCAN": "0" }, ... }
    Nested env: { "zap": { "env": { "ZAP_OPTIONS": "..." } } }
    """
    if not profile_tuning:
        return base
    per_tool: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in base.per_tool.items()}
    for raw_key, payload in profile_tuning.items():
        tk = str(raw_key).strip().lower()
        if not tk or not isinstance(payload, dict):
            continue
        entry = per_tool.setdefault(tk, {})
        env = dict(entry.get("env") or {})
        for ek, ev in payload.items():
            if ek == "env" and isinstance(ev, dict):
                for k2, v2 in ev.items():
                    env[str(k2)] = _stringify_env(v2)
            elif ek == "timeout":
                try:
                    ti = int(ev)
                    if 30 <= ti <= 86400:
                        entry["timeout"] = ti
                except (TypeError, ValueError):
                    pass
            elif ek not in ("meta",):
                env[str(ek)] = _stringify_env(ev)
        entry["env"] = env
        per_tool[tk] = entry
    return ResolvedScanProfile(
        profile=base.profile,
        depth=base.depth,
        intensity=base.intensity,
        coverage=base.coverage,
        per_tool=per_tool,
    )


def _stringify_env(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)
