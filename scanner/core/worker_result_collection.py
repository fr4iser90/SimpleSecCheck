"""
Defaults and merge rules for worker post-scan file collection (manifest.worker_result_collection).

Synced conceptually with worker/infrastructure/worker_result_collection.py fallback dict.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, MutableMapping

# Relative paths under results/<scan_id>/ — prefix-style globs (see worker matcher).
DEFAULT_WORKER_RESULT_COLLECTION: Dict[str, Any] = {
    "include_globs": [
        "summary/**",
        "artifacts/**",
        "tools/**",
    ],
    "exclude_dir_names": [
        ".dotnet",
        "node_modules",
        ".git",
        "__pycache__",
    ],
    "exclude_globs": [],
}


def merge_worker_result_collection(
    base: Dict[str, Any],
    override: MutableMapping[str, Any] | None,
) -> Dict[str, Any]:
    """Deep-merge plugin manifest ``worker_result_collection`` into defaults."""
    out = deepcopy(base)
    if not override:
        return out
    for key, val in override.items():
        if key in ("exclude_dir_names", "include_globs", "exclude_globs") and isinstance(val, list):
            existing = list(out.get(key) or [])
            seen = set()
            merged: List[str] = []
            for item in existing + [str(x) for x in val]:
                if item not in seen:
                    seen.add(item)
                    merged.append(item)
            out[key] = merged
        elif isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out
