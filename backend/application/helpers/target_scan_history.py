"""Serialize scan rows into target history API entries."""
from __future__ import annotations

from typing import Any, Dict, Optional

from domain.datetime_serialization import isoformat_utc

FINISHED_SCAN_STATUSES = ("completed", "failed", "cancelled", "interrupted")


def _extract_branch(config: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(config, dict):
        return None
    for key in ("git_branch", "branch", "branch_name"):
        val = config.get(key)
        if val:
            return str(val)
    return None


def _extract_commit_hash(scan: Any) -> Optional[str]:
    metadata = getattr(scan, "scan_metadata", None) or getattr(scan, "metadata", None) or {}
    if isinstance(metadata, dict):
        commit = metadata.get("commit_hash") or metadata.get("commit")
        if commit:
            return str(commit)
    config = getattr(scan, "config", None) or {}
    if isinstance(config, dict):
        commit = config.get("commit_hash") or config.get("commit")
        if commit:
            return str(commit)
    return None


def scan_to_target_history_entry(scan: Any) -> Dict[str, Any]:
    """Map a Scan entity/model to a history list row."""
    status = getattr(scan.status, "value", scan.status) or str(scan.status)
    config = getattr(scan, "config", None)
    if hasattr(config, "to_dict"):
        config = config.to_dict()
    return {
        "scan_id": str(scan.id),
        "status": str(status).lower(),
        "branch": _extract_branch(config if isinstance(config, dict) else None),
        "commit_hash": _extract_commit_hash(scan),
        "score": None,
        "vulnerabilities": {
            "total": getattr(scan, "total_vulnerabilities", 0) or 0,
            "critical": getattr(scan, "critical_vulnerabilities", 0) or 0,
            "high": getattr(scan, "high_vulnerabilities", 0) or 0,
            "medium": getattr(scan, "medium_vulnerabilities", 0) or 0,
            "low": getattr(scan, "low_vulnerabilities", 0) or 0,
            "info": getattr(scan, "info_vulnerabilities", 0) or 0,
        },
        "created_at": isoformat_utc(getattr(scan, "created_at", None)),
        "completed_at": isoformat_utc(getattr(scan, "completed_at", None)),
    }
