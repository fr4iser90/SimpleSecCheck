"""GitHub repo (user-saved) entity for repository layer."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GitHubRepo:
    """User GitHub repository (saved for scanning)."""
    id: str
    user_id: str
    repo_url: str
    repo_owner: Optional[str]
    repo_name: str
    branch: str
    auto_scan_enabled: bool
    scan_on_push: bool
    scan_frequency: str
    scanners: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    github_token: Optional[str] = None  # Only for internal use; never expose in API
    webhook_secret: Optional[str] = None
