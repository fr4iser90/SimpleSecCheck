"""
Normalize Git hosting *web* URLs (blob/tree views) to clone URLs for git ls-remote / clone.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from domain.entities.target_type import TargetType


def normalize_git_repo_url(url: str) -> str:
    """
    Turn GitHub/GitLab browser URLs into repository roots suitable for git.

    Examples:
      https://github.com/o/r/blob/main/foo/index.html -> https://github.com/o/r.git
      https://gitlab.com/g/p/-/blob/main/README.md -> https://gitlab.com/g/p.git

    If the string does not match a known pattern, it is returned unchanged.
    """
    s = (url or "").strip()
    if not s:
        return s
    try:
        parsed = urlparse(s)
        if not parsed.scheme or not parsed.netloc:
            return s
        host = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # GitHub: https://github.com/owner/repo/blob|tree/branch/...
        if host in ("github.com", "www.github.com"):
            if len(path_parts) >= 4 and path_parts[2] in ("blob", "tree"):
                owner, repo = path_parts[0], path_parts[1]
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return f"{parsed.scheme}://github.com/{owner}/{repo}.git"
            # Plain repo root: .../owner/repo and .../owner/repo.git → same canonical form
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return f"{parsed.scheme}://github.com/{owner}/{repo}.git"
            return s

        # GitLab (hosted or self-hosted): .../-/blob|tree|raw/...
        if "gitlab" in host or host.endswith(".gitlab.com"):
            if "-/" in parsed.path:
                try:
                    idx = path_parts.index("-")
                except ValueError:
                    return s
                if idx + 2 < len(path_parts) and path_parts[idx + 1] in ("blob", "tree", "raw"):
                    project = "/".join(path_parts[:idx])
                    return f"{parsed.scheme}://{parsed.netloc}/{project}.git"

        return s
    except Exception:
        return s


def normalize_repo_url_for_target_type(target_type: str, url: Optional[str]) -> str:
    """Apply `normalize_git_repo_url` only when target_type is git_repo."""
    if target_type != TargetType.GIT_REPO.value:
        return url if url is not None else ""
    return normalize_git_repo_url(url or "")
