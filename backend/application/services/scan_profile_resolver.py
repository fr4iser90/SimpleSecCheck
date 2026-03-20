"""
Build ResolvedScanProfile from DB-synced manifest data (scanner_metadata.scan_profiles).

No tool env defaults here — only reads what plugins declared in manifest.yaml.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from domain.repositories.scanner_repository import ScannerRepository
from domain.value_objects.scan_profile import (
    ResolvedScanProfile,
    ScanProfileName,
    merge_profile_tuning,
    normalize_scan_profile_name,
)


def _stringify_env_val(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


async def resolve_scan_profile_from_manifests(
    *,
    profile: Optional[str],
    profile_tuning: Optional[Dict[str, Any]],
    scanner_repository: ScannerRepository,
) -> ResolvedScanProfile:
    """
    Aggregate scan_profiles from each scanner row (synced from plugin manifest.yaml).

    Falls back to profile name `standard` if a plugin omits the requested key.
    Hints (depth, intensity, coverage): first manifest that defines them wins.
    """
    name = normalize_scan_profile_name(profile)
    scanners = await scanner_repository.list_all()

    per_tool: Dict[str, Dict[str, Any]] = {}
    hint_candidates: list = []

    for sc in scanners:
        meta = sc.scanner_metadata if isinstance(sc.scanner_metadata, dict) else {}
        tk = (meta.get("tools_key") or "").strip().lower()
        if not tk:
            continue

        sp_all = meta.get("scan_profiles")
        if not isinstance(sp_all, dict):
            continue

        prof = sp_all.get(name)
        if not isinstance(prof, dict):
            prof = sp_all.get(ScanProfileName.STANDARD.value)
        if not isinstance(prof, dict):
            continue

        h = prof.get("hints")
        if isinstance(h, dict) and any(h.get(k) for k in ("depth", "intensity", "coverage")):
            hint_candidates.append((tk, h))

        env = prof.get("env")
        if isinstance(env, dict) and env:
            bucket = per_tool.setdefault(tk, {})
            be = bucket.setdefault("env", {})
            for k, v in env.items():
                be[str(k)] = _stringify_env_val(v)

        raw_to = prof.get("timeout")
        if raw_to is not None:
            try:
                ti = int(raw_to)
                if 30 <= ti <= 86400:
                    bucket = per_tool.setdefault(tk, {})
                    bucket["timeout"] = ti
            except (TypeError, ValueError):
                pass

    hints: Dict[str, str] = {}
    if hint_candidates:
        # Prefer semgrep for shared UX labels (code/SAST); else first manifest with hints.
        chosen = next((h for tk, h in hint_candidates if tk == "semgrep"), hint_candidates[0][1])
        for key in ("depth", "intensity", "coverage"):
            if chosen.get(key):
                hints[key] = str(chosen[key]).strip()

    base = ResolvedScanProfile(
        profile=name,
        depth=hints.get("depth") or "medium",
        intensity=hints.get("intensity") or "medium",
        coverage=hints.get("coverage") or "balanced",
        per_tool=per_tool,
    )
    return merge_profile_tuning(base, profile_tuning)
