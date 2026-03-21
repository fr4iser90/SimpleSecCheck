"""
Load merged worker_result_collection from DB (scanner_metadata) and collect scan files.

Defaults must match scanner/core/worker_result_collection.py (orchestrator sync).
"""
from __future__ import annotations

import fnmatch
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Keep in sync with scanner/core/worker_result_collection.DEFAULT_WORKER_RESULT_COLLECTION
_FALLBACK_WORKER_RESULT_COLLECTION: Dict[str, Any] = {
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

_FILE_RESULT_SKIP_SUFFIXES = frozenset(
    {
        ".json",
        ".dll",
        ".so",
        ".dylib",
        ".exe",
        ".pdb",
        ".db",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".7z",
        ".bin",
        ".lock",
    }
)
_MAX_FILE_RESULT_BYTES = 20 * 1024 * 1024

_merged_cache: Optional[Tuple[Dict[str, Any], float]] = None
_MERGED_CACHE_TTL_SEC = 60.0


def invalidate_merged_worker_result_collection_cache() -> None:
    """Call after scanner metadata in DB changes (e.g. POST /api/scanners/refresh)."""
    global _merged_cache
    _merged_cache = None


def _normalize_metadata(sm: Any) -> Optional[Dict[str, Any]]:
    if sm is None:
        return None
    if isinstance(sm, dict):
        return sm
    if isinstance(sm, str):
        try:
            return json.loads(sm)
        except json.JSONDecodeError:
            return None
    return None


async def load_merged_worker_result_collection(database_adapter) -> Dict[str, Any]:
    """
    Union exclude_dir_names / exclude_globs / include_globs from all enabled scanners'
    scanner_metadata.worker_result_collection (filled by orchestrator from manifests).
    """
    global _merged_cache
    now = time.monotonic()
    if _merged_cache is not None:
        data, ts = _merged_cache
        if now - ts < _MERGED_CACHE_TTL_SEC:
            return data

    if not database_adapter:
        return _normalize_merged(_FALLBACK_WORKER_RESULT_COLLECTION)

    include: List[str] = []
    exclude_globs: List[str] = []
    exclude_dir_names: Set[str] = set()
    found_any = False

    try:
        async with database_adapter.get_session() as session:
            result = await session.execute(
                text("SELECT scanner_metadata FROM scanners WHERE enabled = true")
            )
            rows = result.fetchall()
    except Exception as e:
        logger.warning("worker_result_collection: DB read failed, using fallback: %s", e)
        return _normalize_merged(_FALLBACK_WORKER_RESULT_COLLECTION)

    for row in rows:
        sm = _normalize_metadata(row[0] if row else None)
        if not sm:
            continue
        wrc = sm.get("worker_result_collection")
        if not isinstance(wrc, dict):
            continue
        found_any = True
        for d in wrc.get("exclude_dir_names") or []:
            exclude_dir_names.add(str(d).strip())
        for g in wrc.get("exclude_globs") or []:
            g = str(g).strip()
            if g and g not in exclude_globs:
                exclude_globs.append(g)
        for g in wrc.get("include_globs") or []:
            g = str(g).strip()
            if g and g not in include:
                include.append(g)

    if not found_any:
        merged = _normalize_merged(_FALLBACK_WORKER_RESULT_COLLECTION)
    else:
        if not include:
            include = list(_FALLBACK_WORKER_RESULT_COLLECTION["include_globs"])
        if not exclude_dir_names:
            exclude_dir_names = set(_FALLBACK_WORKER_RESULT_COLLECTION["exclude_dir_names"])
        merged = {
            "include_globs": include,
            "exclude_dir_names": frozenset(exclude_dir_names),
            "exclude_globs": exclude_globs,
        }

    _merged_cache = (merged, now)
    return merged


def _normalize_merged(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "include_globs": list(raw.get("include_globs") or []),
        "exclude_dir_names": frozenset(raw.get("exclude_dir_names") or []),
        "exclude_globs": list(raw.get("exclude_globs") or []),
    }


def _rel_matches_include(rel_posix: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    for pat in patterns:
        if _glob_match_scan(rel_posix, pat):
            return True
    return False


def _rel_matches_exclude_glob(rel_posix: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if _glob_match_scan(rel_posix, pat):
            return True
    return False


def _glob_match_scan(rel_posix: str, pattern: str) -> bool:
    """Match path relative to scan root; supports ``prefix/**`` and fnmatch."""
    p = pattern.replace("\\", "/").strip()
    if not p:
        return False
    if p.endswith("/**"):
        base = p[:-3].rstrip("/")
        return rel_posix == base or rel_posix.startswith(base + "/")
    return fnmatch.fnmatch(rel_posix, p) or rel_posix == p


def collect_file_results_for_scan_sync(
    scan_root: Path,
    results_base: Path,
    merged: Dict[str, Any],
) -> Dict[str, str]:
    """Walk ``scan_root`` using merged manifest-driven rules; keys relative to ``results_base``."""
    file_results: Dict[str, str] = {}
    if not scan_root.is_dir():
        return file_results

    skip_dirs: Set[str] = set(merged.get("exclude_dir_names") or [])
    include_globs: List[str] = list(merged.get("include_globs") or [])
    exclude_globs: List[str] = list(merged.get("exclude_globs") or [])

    scan_root_res = scan_root.resolve()
    scan_root_s = str(scan_root_res)
    results_base_s = str(results_base.resolve())

    for root, dirnames, filenames in os.walk(scan_root_s, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            file_path = Path(root) / name
            try:
                rel_to_scan = file_path.resolve().relative_to(scan_root_res)
            except ValueError:
                continue
            rel_posix = rel_to_scan.as_posix()
            if not _rel_matches_include(rel_posix, include_globs):
                continue
            if _rel_matches_exclude_glob(rel_posix, exclude_globs):
                continue

            suf = file_path.suffix.lower()
            if suf in _FILE_RESULT_SKIP_SUFFIXES:
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size == 0 or size > _MAX_FILE_RESULT_BYTES:
                continue
            try:
                rel_key = str(file_path.resolve().relative_to(results_base_s))
            except ValueError:
                rel_key = rel_posix
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if content:
                file_results[rel_key] = content
    return file_results
