"""Read-model entry for repo scan history (last scan / history list)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from domain.datetime_serialization import isoformat_utc


@dataclass
class RepoScanHistoryEntry:
    """Single repo scan history entry."""
    id: str
    repo_id: str
    scan_id: Optional[str]
    branch: Optional[str]
    commit_hash: Optional[str]
    score: Optional[int]
    vulnerabilities: Dict[str, int]
    created_at: datetime

    def to_last_scan_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "created_at": isoformat_utc(self.created_at),
        }
