"""
SQLite Database Adapter (Development)
SQLite-based storage for development environment
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiosqlite

from .adapter import DatabaseAdapter


class SQLiteDatabase(DatabaseAdapter):
    """SQLite database adapter for development"""

    def __init__(self):
        base_dir = Path(os.getenv("SIMPLESECCHECK_ROOT", "/app"))
        default_path = base_dir / "data" / "simpleseccheck.sqlite"
        self.database_path = os.getenv("SQLITE_DB_PATH", str(default_path))
        self.connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize SQLite connection and schema (idempotent)"""
        if self.connection is not None:
            return

        database_path = Path(self.database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = await aiosqlite.connect(self.database_path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        await self.connection.commit()

    async def close(self) -> None:
        """Close SQLite connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                scans_requested INTEGER DEFAULT 0,
                last_rate_limit_reset TEXT,
                rate_limit_scans INTEGER DEFAULT 10,
                rate_limit_requests INTEGER DEFAULT 100,
                ip_address TEXT
            )
            """
        )

        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS queue (
                queue_id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
                repository_url TEXT NOT NULL,
                repository_name TEXT NOT NULL,
                branch TEXT,
                commit_hash TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                position INTEGER,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                scan_id TEXT,
                results_dir TEXT,
                metadata TEXT,
                CONSTRAINT status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
            )
            """
        )

        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_queue_session ON queue(session_id)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_queue_created ON queue(created_at)")

        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_url TEXT NOT NULL,
                branch TEXT NOT NULL,
                commit_hash TEXT NOT NULL,
                scan_id TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                findings_count INTEGER DEFAULT 0,
                metadata_file_path TEXT,
                UNIQUE(repository_url, branch, commit_hash)
            )
            """
        )

        await self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_metadata_repo ON scan_metadata(repository_url, branch, commit_hash)"
        )
        await self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_metadata_date ON scan_metadata(scan_date)"
        )

        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_scans INTEGER DEFAULT 0,
                total_findings INTEGER DEFAULT 0,
                findings_by_severity TEXT DEFAULT '{}',
                findings_by_tool TEXT DEFAULT '{}',
                false_positive_count INTEGER DEFAULT 0,
                UNIQUE(date)
            )
            """
        )

        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_access (
                scan_id TEXT NOT NULL,
                session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (scan_id, session_id)
            )
            """
        )
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_scan_access_scan ON scan_access(scan_id)")
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_scan_access_session ON scan_access(session_id)")

        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_steps (
                scan_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (scan_id, step_number)
            )
            """
        )
        await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_scan_steps_scan ON scan_steps(scan_id)")

    async def _execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        cursor = await self.connection.execute(query, params)
        return cursor

    async def _fetchone(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        cursor = await self._execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def _fetchall(self, query: str, params: tuple = ()) -> List[aiosqlite.Row]:
        cursor = await self._execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    # Session Management
    async def create_session(self, session_id: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session"""
        session_duration = int(os.getenv("SESSION_DURATION", "86400"))
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=session_duration)

        await self._execute(
            """
            INSERT INTO sessions (
                session_id, created_at, expires_at, scans_requested,
                last_rate_limit_reset, rate_limit_scans, rate_limit_requests, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                now.isoformat(),
                expires_at.isoformat(),
                0,
                None,
                int(os.getenv("RATE_LIMIT_PER_SESSION_SCANS", "10")),
                int(os.getenv("RATE_LIMIT_PER_SESSION_REQUESTS", "100")),
                ip_address,
            ),
        )
        await self.connection.commit()

        return {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "scans_requested": 0,
            "last_rate_limit_reset": None,
            "rate_limit_scans": int(os.getenv("RATE_LIMIT_PER_SESSION_SCANS", "10")),
            "rate_limit_requests": int(os.getenv("RATE_LIMIT_PER_SESSION_REQUESTS", "100")),
            "ip_address": ip_address,
        }

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        row = await self._fetchone(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        if not row:
            return None
        return self._row_to_dict(row)

    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        if not kwargs:
            return False

        allowed_fields = {
            "scans_requested",
            "last_rate_limit_reset",
            "rate_limit_scans",
            "rate_limit_requests",
            "ip_address",
            "expires_at",
        }
        sanitized = {key: value for key, value in kwargs.items() if key in allowed_fields}
        if not sanitized:
            return False

        updates = []
        values = []
        for key, value in sanitized.items():
            updates.append(f"{key} = ?")
            values.append(value if not isinstance(value, datetime) else value.isoformat())
        values.append(session_id)

        cursor = await self._execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
            tuple(values),
        )
        await self.connection.commit()
        return cursor.rowcount == 1

    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        cursor = await self._execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await self.connection.commit()
        return cursor.rowcount == 1

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        cursor = await self._execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        await self.connection.commit()
        return cursor.rowcount

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
        position_row = await self._fetchone(
            "SELECT COALESCE(MAX(position), 0) AS max_position FROM queue WHERE status = 'pending'"
        )
        position = (position_row["max_position"] if position_row else 0) + 1
        metadata = None
        if selected_scanners or finding_policy:
            metadata = json.dumps({
                "selected_scanners": selected_scanners,
                "finding_policy": finding_policy,
            })

        await self._execute(
            """
            INSERT INTO queue (
                queue_id, session_id, repository_url, repository_name,
                branch, commit_hash, status, position, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                queue_id,
                session_id,
                repository_url,
                repository_name,
                branch,
                commit_hash,
                "pending",
                position,
                datetime.utcnow().isoformat(),
                metadata,
            ),
        )
        await self.connection.commit()
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
        await self._execute(
            """
            INSERT INTO queue (
                queue_id, session_id, repository_url, repository_name,
                branch, commit_hash, status, position, created_at, completed_at,
                scan_id, results_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                queue_id,
                session_id,
                repository_url,
                repository_name,
                branch,
                commit_hash,
                status,
                None,
                datetime.utcnow().isoformat(),
                completed_at.isoformat() if completed_at else None,
                scan_id,
                results_dir,
            ),
        )
        await self.connection.commit()
        return queue_id

    async def get_queue_item(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get queue item by ID"""
        row = await self._fetchone("SELECT * FROM queue WHERE queue_id = ?", (queue_id,))
        if not row:
            return None
        return self._inject_metadata_fields(self._row_to_dict(row))

    async def get_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get queue items (public, anonymized)"""
        rows = await self._fetchall(
            """
            SELECT queue_id, repository_name, status, position, created_at,
                   scan_id, started_at, completed_at, branch
            FROM queue
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_dict(row) for row in rows]

    async def get_queue_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queue items for a specific session"""
        rows = await self._fetchall(
            "SELECT * FROM queue WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        return [self._row_to_dict(row) for row in rows]

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
        updates = ["status = ?"]
        values: List[Any] = [status]

        if scan_id:
            updates.append("scan_id = ?")
            values.append(scan_id)
        if started_at:
            updates.append("started_at = ?")
            values.append(started_at.isoformat())
        if completed_at:
            updates.append("completed_at = ?")
            values.append(completed_at.isoformat())
        if results_dir:
            updates.append("results_dir = ?")
            values.append(results_dir)

        values.append(queue_id)
        cursor = await self._execute(
            f"UPDATE queue SET {', '.join(updates)} WHERE queue_id = ?",
            tuple(values),
        )
        await self.connection.commit()
        return cursor.rowcount == 1

    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        """Get next pending queue item (FIFO)"""
        row = await self._fetchone(
            """
            SELECT * FROM queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        if not row:
            return None
        return self._inject_metadata_fields(self._row_to_dict(row))

    async def get_queue_length(self) -> int:
        """Get current queue length (active items only)"""
        row = await self._fetchone(
            "SELECT COUNT(*) AS count FROM queue WHERE status IN ('pending', 'running')"
        )
        return int(row["count"]) if row else 0

    async def cleanup_old_queue_items(self, max_age_days: int = 7) -> int:
        """Clean up old completed/failed queue items"""
        cursor = await self._execute(
            """
            DELETE FROM queue
            WHERE status IN ('completed', 'failed')
              AND completed_at IS NOT NULL
              AND completed_at < datetime('now', ?)
            """,
            (f"-{max_age_days} days",),
        )
        await self.connection.commit()
        return cursor.rowcount

    async def find_duplicate_in_queue(
        self,
        repository_url: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        finding_policy: Optional[str] = None,
        include_completed: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Find duplicate scan in queue"""
        normalized_url = self._normalize_url(repository_url)

        query = "SELECT * FROM queue WHERE repository_url = ?"
        values: List[Any] = [normalized_url]

        if branch:
            query += " AND branch = ?"
            values.append(branch)
        if commit_hash:
            query += " AND commit_hash = ?"
            values.append(commit_hash)
        if finding_policy is not None:
            query += " AND json_extract(metadata, '$.finding_policy') = ?"
            values.append(finding_policy)

        if include_completed:
            query += " AND status IN ('pending', 'running', 'completed')"
        else:
            query += " AND status IN ('pending', 'running')"
        query += " LIMIT 1"

        row = await self._fetchone(query, tuple(values))
        if not row:
            return None
        return self._inject_metadata_fields(self._row_to_dict(row))

    async def add_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Grant a session access to a scan"""
        await self._execute(
            """
            INSERT OR IGNORE INTO scan_access (scan_id, session_id, created_at)
            VALUES (?, ?, ?)
            """,
            (scan_id, session_id, datetime.utcnow().isoformat()),
        )
        await self.connection.commit()
        return True

    async def has_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Check if a session has access to a scan"""
        row = await self._fetchone(
            "SELECT 1 FROM scan_access WHERE scan_id = ? AND session_id = ?",
            (scan_id, session_id),
        )
        return bool(row)

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
        normalized_url = self._normalize_url(repository_url)
        now = datetime.utcnow().isoformat()

        await self._execute(
            """
            INSERT INTO scan_metadata (
                repository_url, branch, commit_hash, scan_id,
                scan_date, findings_count, metadata_file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository_url, branch, commit_hash)
            DO UPDATE SET
                scan_id = excluded.scan_id,
                scan_date = excluded.scan_date,
                findings_count = excluded.findings_count,
                metadata_file_path = excluded.metadata_file_path
            """,
            (
                normalized_url,
                branch,
                commit_hash,
                scan_id,
                now,
                findings_count,
                metadata_file_path,
            ),
        )
        await self.connection.commit()
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
        max_age = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()

        row = await self._fetchone(
            """
            SELECT * FROM scan_metadata
            WHERE repository_url = ?
              AND branch = ?
              AND commit_hash = ?
              AND scan_date > ?
            ORDER BY scan_date DESC
            LIMIT 1
            """,
            (normalized_url, branch, commit_hash, max_age),
        )
        if not row:
            return None
        return self._row_to_dict(row)

    # Statistics
    async def increment_statistics(
        self,
        findings_by_severity: Dict[str, int],
        findings_by_tool: Dict[str, int],
        false_positive_count: int = 0,
    ) -> bool:
        """Increment statistics counters"""
        today = datetime.utcnow().date().isoformat()
        total_findings = sum(findings_by_severity.values())

        row = await self._fetchone(
            "SELECT findings_by_severity, findings_by_tool FROM statistics WHERE date = ?",
            (today,),
        )

        if row:
            existing_severity = json.loads(row["findings_by_severity"] or "{}")
            existing_tool = json.loads(row["findings_by_tool"] or "{}")

            merged_severity = dict(existing_severity)
            for key, value in findings_by_severity.items():
                merged_severity[key] = merged_severity.get(key, 0) + value

            merged_tool = dict(existing_tool)
            for key, value in findings_by_tool.items():
                merged_tool[key] = merged_tool.get(key, 0) + value

            await self._execute(
                """
                UPDATE statistics SET
                    total_scans = total_scans + 1,
                    total_findings = total_findings + ?,
                    findings_by_severity = ?,
                    findings_by_tool = ?,
                    false_positive_count = false_positive_count + ?
                WHERE date = ?
                """,
                (
                    total_findings,
                    json.dumps(merged_severity),
                    json.dumps(merged_tool),
                    false_positive_count,
                    today,
                ),
            )
        else:
            await self._execute(
                """
                INSERT INTO statistics (
                    date, total_scans, total_findings,
                    findings_by_severity, findings_by_tool, false_positive_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    today,
                    1,
                    total_findings,
                    json.dumps(findings_by_severity),
                    json.dumps(findings_by_tool),
                    false_positive_count,
                ),
            )

        await self.connection.commit()
        return True

    async def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        rows = await self._fetchall(
            "SELECT total_scans, total_findings, false_positive_count, findings_by_severity, findings_by_tool FROM statistics"
        )

        if not rows:
            return {
                "total_scans": 0,
                "total_findings": 0,
                "findings_by_severity": {},
                "findings_by_tool": {},
                "false_positive_rate": 0.0,
            }

        total_scans = 0
        total_findings = 0
        false_positive_count = 0
        findings_by_severity: Dict[str, int] = {}
        findings_by_tool: Dict[str, int] = {}

        for row in rows:
            total_scans += row["total_scans"] or 0
            total_findings += row["total_findings"] or 0
            false_positive_count += row["false_positive_count"] or 0

            severity_json = json.loads(row["findings_by_severity"] or "{}")
            tool_json = json.loads(row["findings_by_tool"] or "{}")

            for key, value in severity_json.items():
                findings_by_severity[key] = findings_by_severity.get(key, 0) + int(value)
            for key, value in tool_json.items():
                findings_by_tool[key] = findings_by_tool.get(key, 0) + int(value)

        false_positive_rate = 0.0
        if total_findings > 0:
            false_positive_rate = false_positive_count / total_findings

        return {
            "total_scans": total_scans,
            "total_findings": total_findings,
            "findings_by_severity": findings_by_severity,
            "findings_by_tool": findings_by_tool,
            "false_positive_rate": false_positive_rate,
        }

    # Step Tracking
    async def upsert_scan_step(
        self,
        scan_id: str,
        step_number: int,
        step_name: str,
        status: str,
        message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        await self._execute(
            """
            INSERT INTO scan_steps (
                scan_id, step_number, step_name, status, message,
                started_at, completed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scan_id, step_number) DO UPDATE SET
                step_name = excluded.step_name,
                status = excluded.status,
                message = excluded.message,
                started_at = COALESCE(excluded.started_at, scan_steps.started_at),
                completed_at = COALESCE(excluded.completed_at, scan_steps.completed_at),
                updated_at = excluded.updated_at
            """,
            (
                scan_id,
                step_number,
                step_name,
                status,
                message,
                started_at.isoformat() if started_at else None,
                completed_at.isoformat() if completed_at else None,
                datetime.utcnow().isoformat(),
            ),
        )
        await self.connection.commit()
        return True

    async def get_scan_steps(self, scan_id: str) -> List[Dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT step_number, step_name, status, message
            FROM scan_steps
            WHERE scan_id = ?
            ORDER BY step_number ASC
            """,
            (scan_id,),
        )
        return [
            {
                "number": row["step_number"],
                "name": row["step_name"],
                "status": row["status"],
                "message": row["message"],
            }
            for row in rows
        ]

    def _normalize_url(self, url: str) -> str:
        """Normalize repository URL"""
        url = url.rstrip(".git").rstrip("/")
        if url.startswith("git@"):
            url = url.replace("git@", "https://").replace(":", "/")
        return url

    def _row_to_dict(self, row: aiosqlite.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def _inject_metadata_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if "metadata" in result and result["metadata"]:
            try:
                metadata = json.loads(result["metadata"]) if isinstance(result["metadata"], str) else result["metadata"]
                if isinstance(metadata, dict):
                    if "selected_scanners" in metadata:
                        result["selected_scanners"] = metadata["selected_scanners"]
                    if "finding_policy" in metadata:
                        result["finding_policy"] = metadata["finding_policy"]
            except (json.JSONDecodeError, TypeError):
                pass
        return result