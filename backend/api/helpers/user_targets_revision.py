"""Compute My Targets list revision for SSE (lazy import of route assembly)."""
from __future__ import annotations


async def compute_user_targets_list_revision(user_id: str) -> str:
    from api.routes.user import assemble_user_scan_targets_list, compute_targets_revision
    from infrastructure.container import get_scan_repository, get_scan_target_service

    svc = get_scan_target_service()
    repo = get_scan_repository()
    rows = await assemble_user_scan_targets_list(str(user_id), None, svc, repo)
    return compute_targets_revision(rows)
