"""
Lightweight Git remote helpers (ls-remote) for scheduler diff checks.
"""
from __future__ import annotations

import logging
import subprocess  # nosec B404
from typing import Optional

from domain.utils.git_repo_url import normalize_git_repo_url

logger = logging.getLogger(__name__)


def resolve_branch_head_sha(
    repo_url: str,
    branch: str,
    *,
    timeout: int = 15,
) -> Optional[str]:
    """
    Resolve the current commit SHA for a branch via ``git ls-remote`` (no clone).

    Returns None if the ref cannot be resolved (private repo without creds, network, etc.).
    """
    url = normalize_git_repo_url((repo_url or "").strip())
    branch_name = (branch or "main").strip()
    if not url or not branch_name:
        return None

    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "ls-remote", url, f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("git ls-remote timed out for %s (branch %s)", url, branch_name)
        return None
    except FileNotFoundError:
        logger.warning("git binary not available for ls-remote")
        return None

    if result.returncode != 0:
        logger.debug(
            "git ls-remote failed for %s branch %s: %s",
            url,
            branch_name,
            (result.stderr or "").strip()[:200],
        )
        return None

    for line in (result.stdout or "").strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 1:
            sha = parts[0].strip()
            if sha:
                return sha
    return None
