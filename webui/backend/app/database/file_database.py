"""
File-Based Database Adapter (Development)
Simple file-based storage for development environment
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib
from .adapter import DatabaseAdapter


class FileDatabase(DatabaseAdapter):
    """File-based database adapter for development"""
    
    def __init__(self):
        self.base_dir = Path(os.getenv("SIMPLESECCHECK_ROOT", "/app"))
        self.data_dir = self.base_dir / "data"
        self.sessions_dir = self.data_dir / "sessions"
        self.queue_file = self.data_dir / "queue.json"
        self.metadata_dir = self.data_dir / "metadata"
        self.statistics_file = self.data_dir / "statistics.json"
        
        # In-memory storage for sessions and queue
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._queue: List[Dict[str, Any]] = []
        self._statistics: Dict[str, Any] = {
            "total_scans": 0,
            "total_findings": 0,
            "findings_by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            },
            "findings_by_tool": {},
            "false_positive_count": 0,
        }
    
    async def initialize(self) -> None:
        """Initialize file-based database (idempotent)"""
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Load queue from file if exists
        if self.queue_file.exists():
            try:
                with open(self.queue_file, "r") as f:
                    self._queue = json.load(f)
            except Exception:
                self._queue = []
        
        # Load statistics from file if exists
        if self.statistics_file.exists():
            try:
                with open(self.statistics_file, "r") as f:
                    self._statistics = json.load(f)
            except Exception:
                pass
    
    async def close(self) -> None:
        """Save data to files"""
        # Save queue
        with open(self.queue_file, "w") as f:
            json.dump(self._queue, f, indent=2, default=str)
        
        # Save statistics
        with open(self.statistics_file, "w") as f:
            json.dump(self._statistics, f, indent=2)
    
    # Session Management
    async def create_session(self, session_id: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session"""
        session_duration = int(os.getenv("SESSION_DURATION", "86400"))  # 24 hours
        now = datetime.utcnow()
        
        session = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=session_duration)).isoformat(),
            "scans_requested": 0,
            "rate_limit_scans": int(os.getenv("RATE_LIMIT_PER_SESSION_SCANS", "10")),
            "rate_limit_requests": int(os.getenv("RATE_LIMIT_PER_SESSION_REQUESTS", "100")),
            "ip_address": ip_address,
        }
        
        self._sessions[session_id] = session
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self._sessions.get(session_id)
    
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        if session_id not in self._sessions:
            return False
        
        self._sessions[session_id].update(kwargs)
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._sessions.items()
            if datetime.fromisoformat(session["expires_at"]) < now
        ]
        
        for sid in expired:
            del self._sessions[sid]
        
        return len(expired)
    
    # Queue Management
    async def add_to_queue(
        self,
        session_id: str,
        repository_url: str,
        repository_name: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        selected_scanners: Optional[List[str]] = None,
        finding_policy: Optional[str] = None,
    ) -> str:
        """Add scan to queue"""
        queue_id = str(uuid.uuid4())
        pending_positions = [q.get("position") for q in self._queue if q.get("status") == "pending" and q.get("position")]
        position = (max(pending_positions) if pending_positions else 0) + 1
        
        queue_item = {
            "queue_id": queue_id,
            "session_id": session_id,
            "repository_url": repository_url,
            "repository_name": repository_name,
            "branch": branch,
            "commit_hash": commit_hash,
            "selected_scanners": selected_scanners,  # List of scanner names
            "finding_policy": finding_policy,
            "status": "pending",
            "position": position,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "scan_id": None,
        }
        
        self._queue.append(queue_item)
        return queue_id

    async def add_queue_item_for_session(
        self,
        session_id: str,
        repository_url: str,
        repository_name: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        status: str = "completed",
        scan_id: Optional[str] = None,
        results_dir: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> str:
        """Add a queue item for a session with predefined status/scan_id"""
        queue_id = str(uuid.uuid4())
        queue_item = {
            "queue_id": queue_id,
            "session_id": session_id,
            "repository_url": repository_url,
            "repository_name": repository_name,
            "branch": branch,
            "commit_hash": commit_hash,
            "selected_scanners": None,
            "finding_policy": None,
            "status": status,
            "position": None,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "scan_id": scan_id,
            "results_dir": results_dir,
        }
        self._queue.append(queue_item)
        return queue_id
    
    async def get_queue_item(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get queue item by ID"""
        for item in self._queue:
            if item["queue_id"] == queue_id:
                return self._inject_metadata_fields(item)
        return None
    
    async def get_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get queue items (public, anonymized)"""
        # Return only public fields (anonymized)
        public_queue = []
        for item in self._queue[:limit]:
            public_item = {
                "queue_id": item["queue_id"],
                "repository_name": item["repository_name"],  # Already anonymized
                "status": item["status"],  # Backend standard: pending, running, completed, failed
                "position": item["position"],
                "created_at": item["created_at"],
                "branch": item.get("branch"),  # Include branch if available
            }
            public_queue.append(public_item)
        
        return public_queue
    
    async def get_queue_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queue items for a specific session"""
        return [item for item in self._queue if item["session_id"] == session_id]
    
    async def update_queue_status(
        self,
        queue_id: str,
        status: str,
        scan_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        results_dir: Optional[str] = None,
    ) -> bool:
        """Update queue item status"""
        for item in self._queue:
            if item["queue_id"] == queue_id:
                item["status"] = status
                if scan_id:
                    item["scan_id"] = scan_id
                if started_at:
                    item["started_at"] = started_at.isoformat()
                if completed_at:
                    item["completed_at"] = completed_at.isoformat()
                if results_dir:
                    item["results_dir"] = results_dir
                return True
        return False
    
    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        """Get next pending queue item (FIFO)"""
        pending = [item for item in self._queue if item["status"] == "pending"]
        if not pending:
            return None
        
        # Sort by created_at (FIFO)
        pending.sort(key=lambda x: x["created_at"])
        return self._inject_metadata_fields(pending[0])
    
    async def get_queue_length(self) -> int:
        """Get current queue length (active items only)"""
        return len([item for item in self._queue if item.get("status") in ("pending", "running")])
    
    async def cleanup_old_queue_items(self, max_age_days: int = 7) -> int:
        """Clean up old completed/failed queue items"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        initial_length = len(self._queue)
        
        self._queue = [
            item for item in self._queue
            if not (
                item["status"] in ("completed", "failed")
                and item.get("completed_at")
                and datetime.fromisoformat(item["completed_at"]) < cutoff_date
            )
        ]
        
        deleted_count = initial_length - len(self._queue)
        return deleted_count
    
    async def find_duplicate_in_queue(
        self,
        repository_url: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        finding_policy: Optional[str] = None,
        include_completed: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Find duplicate scan in queue"""
        for item in self._queue:
            if item["repository_url"] == repository_url:
                if not include_completed and item.get("status") not in ("pending", "running"):
                    continue
                if branch and item.get("branch") != branch:
                    continue
                if commit_hash and item.get("commit_hash") != commit_hash:
                    continue
                if finding_policy is not None and item.get("finding_policy") != finding_policy:
                    continue
                # Found duplicate
                return item
        return None

    async def add_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Grant a session access to a scan (dev storage)"""
        for item in self._queue:
            if item.get("scan_id") == scan_id:
                allowed = item.setdefault("allowed_sessions", [])
                if session_id not in allowed:
                    allowed.append(session_id)
                return True
        return False

    async def has_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Check if a session has access to a scan (dev storage)"""
        for item in self._queue:
            if item.get("scan_id") == scan_id:
                allowed = item.get("allowed_sessions", [])
                return session_id in allowed
        return False
    
    # Metadata Management
    async def save_scan_metadata(
        self,
        repository_url: str,
        branch: str,
        commit_hash: str,
        scan_id: str,
        findings_count: int,
        metadata_file_path: Optional[str] = None,
    ) -> bool:
        """Save scan metadata for deduplication"""
        # Normalize URL
        normalized_url = self._normalize_url(repository_url)
        
        # Create metadata file
        metadata = {
            "repository_url": normalized_url,
            "branch": branch,
            "commit_hash": commit_hash,
            "scan_id": scan_id,
            "scan_date": datetime.utcnow().isoformat(),
            "findings_count": findings_count,
            "metadata_file_path": metadata_file_path,
        }
        
        # Save to file
        metadata_file = self.metadata_dir / f"{scan_id}.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return True
    
    async def find_duplicate_scan(
        self,
        repository_url: str,
        branch: str,
        commit_hash: str,
        max_age_days: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """Find duplicate scan by metadata"""
        normalized_url = self._normalize_url(repository_url)
        max_age = datetime.utcnow() - timedelta(days=max_age_days)
        
        # Search metadata files
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                
                if (metadata["repository_url"] == normalized_url and
                    metadata["branch"] == branch and
                    metadata["commit_hash"] == commit_hash):
                    
                    scan_date = datetime.fromisoformat(metadata["scan_date"])
                    if scan_date > max_age:
                        return metadata
            except Exception as exc:
                print(f"[FileDatabase] Failed to read metadata file {metadata_file}: {exc}")
                continue
        
        return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize repository URL"""
        # Remove .git suffix
        url = url.rstrip(".git")
        # Remove trailing slash
        url = url.rstrip("/")
        # Convert git@ to https://
        if url.startswith("git@"):
            url = url.replace("git@", "https://").replace(":", "/")
        return url

    def _inject_metadata_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata fields into top-level keys"""
        return item
    
    # Statistics
    async def increment_statistics(
        self,
        findings_by_severity: Dict[str, int],
        findings_by_tool: Dict[str, int],
        false_positive_count: int = 0,
    ) -> bool:
        """Increment statistics counters"""
        self._statistics["total_scans"] += 1
        
        for severity, count in findings_by_severity.items():
            if severity in self._statistics["findings_by_severity"]:
                self._statistics["findings_by_severity"][severity] += count
            self._statistics["total_findings"] += count
        
        for tool, count in findings_by_tool.items():
            if tool not in self._statistics["findings_by_tool"]:
                self._statistics["findings_by_tool"][tool] = 0
            self._statistics["findings_by_tool"][tool] += count
        
        self._statistics["false_positive_count"] += false_positive_count
        
        return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        total_findings = sum(self._statistics["findings_by_severity"].values())
        false_positive_rate = 0.0
        if total_findings > 0:
            false_positive_rate = self._statistics["false_positive_count"] / total_findings
        
        return {
            "total_scans": self._statistics["total_scans"],
            "total_findings": total_findings,
            "findings_by_severity": self._statistics["findings_by_severity"],
            "findings_by_tool": self._statistics["findings_by_tool"],
            "false_positive_rate": false_positive_rate,
        }
