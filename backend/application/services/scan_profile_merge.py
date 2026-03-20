"""
Merge resolved scan profile (env + per-profile timeout from manifests) into scanner_tool_overrides.

Profile env is merged first; existing admin-derived env on the same key wins (secrets).
When the manifest defines scan_profiles.<name>.timeout, it becomes the tool timeout for this scan.
"""
from __future__ import annotations

import copy
from typing import Any, Dict

from domain.value_objects.scan_profile import ResolvedScanProfile


def merge_resolved_profile_into_overrides(
    merged: Dict[str, Dict[str, Any]],
    resolved: ResolvedScanProfile,
) -> Dict[str, Dict[str, Any]]:
    """
    merged: output of build_merged_tool_overrides()
    resolved: from resolve_scan_profile_from_manifests()
    """
    out: Dict[str, Dict[str, Any]] = copy.deepcopy(merged) if merged else {}

    for tk, pdata in resolved.per_tool.items():
        pdata = pdata or {}
        prof_env = pdata.get("env") or {}
        prof_timeout = pdata.get("timeout")

        if not prof_env and prof_timeout is None:
            continue

        if tk not in out:
            out[tk] = {
                "timeout": None,
                "enabled": True,
                "config": {},
                "env": {},
                "tools_key": tk,
            }
        entry = out[tk]
        admin_env = entry.get("env") if isinstance(entry.get("env"), dict) else {}
        entry["env"] = {**prof_env, **admin_env}

        if prof_timeout is not None:
            try:
                ti = int(prof_timeout)
                if 30 <= ti <= 86400:
                    entry["timeout"] = ti
            except (TypeError, ValueError):
                pass

        out[tk] = entry

    return out
