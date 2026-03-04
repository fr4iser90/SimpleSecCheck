"""
PostgreSQL Database Adapter (Production)
PostgreSQL-based storage for production environment
"""

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncpg
from .adapter import DatabaseAdapter


class PostgreSQLDatabase(DatabaseAdapter):
    """PostgreSQL database adapter for production"""
    
    def __init__(self):
        self.connection_pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")
        
        # Validate DATABASE_URL format
        if not self.database_url.startswith("postgresql://"):
            raise ValueError(f"Invalid DATABASE_URL format: must start with 'postgresql://' (got: {self.database_url[:20]}...)")
        
        print(f"[PostgreSQL] Using DATABASE_URL: postgresql://***:***@***/***")
    
    async def initialize(self) -> None:
        """Initialize PostgreSQL connection pool with retry logic (idempotent)"""
        # If already initialized, skip
        if self.connection_pool is not None:
            return
        
        max_retries = 10
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                self.connection_pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                )
                
                # Test connection
                async with self.connection_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                
                print(f"[PostgreSQL] Connection pool initialized successfully")
                
                # Create tables if they don't exist
                await self._create_tables()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[PostgreSQL] Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"[PostgreSQL] Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"[PostgreSQL] Failed to connect after {max_retries} attempts: {e}")
                    raise
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
    
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        async with self.connection_pool.acquire() as conn:
            # Sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id UUID PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    scans_requested INTEGER DEFAULT 0,
                    rate_limit_scans INTEGER DEFAULT 10,
                    rate_limit_requests INTEGER DEFAULT 100,
                    ip_address TEXT
                )
            """)
            
            # Queue table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    queue_id UUID PRIMARY KEY,
                    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                    repository_url TEXT NOT NULL,
                    repository_name TEXT NOT NULL,
                    branch TEXT,
                    commit_hash TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    position INTEGER,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    scan_id TEXT,
                    results_dir TEXT,
                    metadata JSONB,
                    CONSTRAINT status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
                )
            """)
            
            # Add metadata column if it doesn't exist (migration for existing databases)
            await conn.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'queue' AND column_name = 'metadata'
                    ) THEN
                        ALTER TABLE queue ADD COLUMN metadata JSONB;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'queue' AND column_name = 'results_dir'
                    ) THEN
                        ALTER TABLE queue ADD COLUMN results_dir TEXT;
                    END IF;
                END $$;
            """)
            
            # Create index for faster queue lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_session ON queue(session_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_created ON queue(created_at)
            """)
            
            # Metadata table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_metadata (
                    id SERIAL PRIMARY KEY,
                    repository_url TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    scan_id TEXT NOT NULL,
                    scan_date TIMESTAMP NOT NULL DEFAULT NOW(),
                    findings_count INTEGER DEFAULT 0,
                    metadata_file_path TEXT,
                    UNIQUE(repository_url, branch, commit_hash)
                )
            """)
            
            # Create index for faster metadata lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_repo ON scan_metadata(repository_url, branch, commit_hash)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_date ON scan_metadata(scan_date)
            """)
            
            # Statistics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL DEFAULT CURRENT_DATE,
                    total_scans INTEGER DEFAULT 0,
                    total_findings INTEGER DEFAULT 0,
                    findings_by_severity JSONB DEFAULT '{}',
                    findings_by_tool JSONB DEFAULT '{}',
                    false_positive_count INTEGER DEFAULT 0,
                    UNIQUE(date)
                )
            """)

            # Scan access table (allows multiple sessions to access same scan)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_access (
                    scan_id TEXT NOT NULL,
                    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (scan_id, session_id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_access_scan ON scan_access(scan_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_access_session ON scan_access(session_id)
            """)
    
    # Session Management
    async def create_session(self, session_id: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session"""
        session_duration = int(os.getenv("SESSION_DURATION", "86400"))  # 24 hours
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=session_duration)
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (session_id, created_at, expires_at, ip_address)
                VALUES ($1, $2, $3, $4)
            """, uuid.UUID(session_id), now, expires_at, ip_address)
        
        return {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "scans_requested": 0,
            "rate_limit_scans": int(os.getenv("RATE_LIMIT_PER_SESSION_SCANS", "10")),
            "rate_limit_requests": int(os.getenv("RATE_LIMIT_PER_SESSION_REQUESTS", "100")),
            "ip_address": ip_address,
        }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM sessions WHERE session_id = $1
            """, uuid.UUID(session_id))
            
            if not row:
                return None
            
            return {
                "session_id": str(row["session_id"]),
                "created_at": row["created_at"].isoformat(),
                "expires_at": row["expires_at"].isoformat(),
                "scans_requested": row["scans_requested"],
                "rate_limit_scans": row["rate_limit_scans"],
                "rate_limit_requests": row["rate_limit_requests"],
                "ip_address": row["ip_address"],
            }
    
    async def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        if not kwargs:
            return False

        # Only allow known session columns to be updated
        allowed_fields = {
            "scans_requested",
            "rate_limit_scans",
            "rate_limit_requests",
            "ip_address",
            "expires_at",
        }

        # Filter kwargs to allowed fields
        sanitized = {key: value for key, value in kwargs.items() if key in allowed_fields}
        if not sanitized:
            return False

        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE sessions SET
                    scans_requested = COALESCE($1, scans_requested),
                    rate_limit_scans = COALESCE($2, rate_limit_scans),
                    rate_limit_requests = COALESCE($3, rate_limit_requests),
                    ip_address = COALESCE($4, ip_address),
                    expires_at = COALESCE($5, expires_at)
                WHERE session_id = $6
                """,
                sanitized.get("scans_requested"),
                sanitized.get("rate_limit_scans"),
                sanitized.get("rate_limit_requests"),
                sanitized.get("ip_address"),
                sanitized.get("expires_at"),
                uuid.UUID(session_id),
            )

            return result == "UPDATE 1"
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM sessions WHERE session_id = $1
            """, uuid.UUID(session_id))
            
            return result == "DELETE 1"
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM sessions WHERE expires_at < NOW()
            """)
            
            # Extract count from result string "DELETE N"
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
    
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
        import json
        queue_id = str(uuid.uuid4())
        
        # Calculate position (count of pending items)
        async with self.connection_pool.acquire() as conn:
            # Use a transaction + table lock to ensure unique, monotonic positions
            async with conn.transaction():
                await conn.execute("LOCK TABLE queue IN SHARE ROW EXCLUSIVE MODE")
                position_result = await conn.fetchval("""
                    SELECT COALESCE(MAX(position), 0) FROM queue WHERE status = 'pending'
                """)
                position = (position_result or 0) + 1

                # Try to insert with selected_scanners in metadata field (if column exists)
                # If column doesn't exist, we'll store it in a text field or skip it
                try:
                    await conn.execute("""
                        INSERT INTO queue (
                            queue_id, session_id, repository_url, repository_name,
                            branch, commit_hash, status, position, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, uuid.UUID(queue_id), uuid.UUID(session_id), repository_url,
                        repository_name, branch, commit_hash, "pending", position,
                        json.dumps({
                            "selected_scanners": selected_scanners,
                            "finding_policy": finding_policy,
                        }) if selected_scanners or finding_policy else None)
                except Exception:
                    # Fallback: if metadata column doesn't exist, try without it
                    await conn.execute("""
                        INSERT INTO queue (
                            queue_id, session_id, repository_url, repository_name,
                            branch, commit_hash, status, position
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """, uuid.UUID(queue_id), uuid.UUID(session_id), repository_url,
                        repository_name, branch, commit_hash, "pending", position)
        
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
        async with self.connection_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO queue (
                    queue_id, session_id, repository_url, repository_name,
                    branch, commit_hash, status, position, scan_id, results_dir, completed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                uuid.UUID(queue_id),
                uuid.UUID(session_id),
                repository_url,
                repository_name,
                branch,
                commit_hash,
                status,
                None,
                scan_id,
                results_dir,
                completed_at,
            )
        return queue_id
    
    async def get_queue_item(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """Get queue item by ID"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM queue WHERE queue_id = $1
            """, uuid.UUID(queue_id))
            
            if not row:
                return None
            
            return self._inject_metadata_fields(self._row_to_dict(row))
    
    async def get_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get queue items (public, anonymized) - includes all statuses"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT queue_id, repository_name, status, position, created_at, scan_id, started_at, completed_at, branch
                FROM queue
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            
            return [self._row_to_dict(row) for row in rows]
    
    async def get_queue_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queue items for a specific session"""
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM queue WHERE session_id = $1 ORDER BY created_at ASC
            """, uuid.UUID(session_id))
            
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
        updates = ["status = $1"]
        values = [status]
        param_num = 2
        
        if scan_id:
            updates.append(f"scan_id = ${param_num}")
            values.append(scan_id)
            param_num += 1
        
        if started_at:
            updates.append(f"started_at = ${param_num}")
            values.append(started_at)
            param_num += 1
        
        if completed_at:
            updates.append(f"completed_at = ${param_num}")
            values.append(completed_at)
            param_num += 1

        if results_dir:
            updates.append(f"results_dir = ${param_num}")
            values.append(results_dir)
            param_num += 1
        
        values.append(uuid.UUID(queue_id))
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(f"""
                UPDATE queue SET {', '.join(updates)}
                WHERE queue_id = ${param_num}
            """, *values)
            
            return result == "UPDATE 1"
    
    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        """Get next pending queue item (FIFO)"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM queue
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            
            if not row:
                return None
            
            return self._inject_metadata_fields(self._row_to_dict(row))
    
    async def get_queue_length(self) -> int:
        """Get current queue length (active items only)"""
        async with self.connection_pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM queue
                WHERE status IN ('pending', 'running')
            """)
            return count or 0
    
    async def cleanup_old_queue_items(self, max_age_days: int = 7) -> int:
        """Clean up old completed/failed queue items"""
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM queue
                WHERE status IN ('completed', 'failed')
                AND completed_at < NOW() - INTERVAL '%s days'
            """, max_age_days)
            
            # Extract count from result string "DELETE N"
            return int(result.split()[-1]) if result.startswith("DELETE") else 0
    
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
        
        query = "SELECT * FROM queue WHERE repository_url = $1"
        values = [normalized_url]
        param_num = 2
        
        if branch:
            query += f" AND branch = ${param_num}"
            values.append(branch)
            param_num += 1
        
        if commit_hash:
            query += f" AND commit_hash = ${param_num}"
            values.append(commit_hash)
            param_num += 1

        if finding_policy is not None:
            query += f" AND metadata->>'finding_policy' = ${param_num}"
            values.append(finding_policy)
            param_num += 1

        if include_completed:
            query += " AND status IN ('pending', 'running', 'completed')"
        else:
            query += " AND status IN ('pending', 'running')"
        query += " LIMIT 1"
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            
            if not row:
                return None
            
            return self._row_to_dict(row)

    async def add_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Grant a session access to a scan"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scan_access (scan_id, session_id)
                VALUES ($1, $2)
                ON CONFLICT (scan_id, session_id) DO NOTHING
                """,
                scan_id,
                uuid.UUID(session_id),
            )
        return True

    async def has_scan_access(self, scan_id: str, session_id: str) -> bool:
        """Check if a session has access to a scan"""
        async with self.connection_pool.acquire() as conn:
            exists = await conn.fetchval(
                """
                SELECT 1 FROM scan_access WHERE scan_id = $1 AND session_id = $2
                """,
                scan_id,
                uuid.UUID(session_id),
            )
            return bool(exists)
    
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
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO scan_metadata (
                    repository_url, branch, commit_hash, scan_id,
                    findings_count, metadata_file_path
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (repository_url, branch, commit_hash)
                DO UPDATE SET
                    scan_id = EXCLUDED.scan_id,
                    scan_date = EXCLUDED.scan_date,
                    findings_count = EXCLUDED.findings_count,
                    metadata_file_path = EXCLUDED.metadata_file_path
            """, normalized_url, branch, commit_hash, scan_id,
                findings_count, metadata_file_path)
        
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
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM scan_metadata
                WHERE repository_url = $1
                  AND branch = $2
                  AND commit_hash = $3
                  AND scan_date > $4
                ORDER BY scan_date DESC
                LIMIT 1
            """, normalized_url, branch, commit_hash, max_age)
            
            if not row:
                return None
            
            return {
                "repository_url": row["repository_url"],
                "branch": row["branch"],
                "commit_hash": row["commit_hash"],
                "scan_id": row["scan_id"],
                "scan_date": row["scan_date"].isoformat(),
                "findings_count": row["findings_count"],
                "metadata_file_path": row["metadata_file_path"],
            }
    
    def _normalize_url(self, url: str) -> str:
        """Normalize repository URL"""
        url = url.rstrip(".git").rstrip("/")
        if url.startswith("git@"):
            url = url.replace("git@", "https://").replace(":", "/")
        return url
    
    # Statistics
    async def increment_statistics(
        self,
        findings_by_severity: Dict[str, int],
        findings_by_tool: Dict[str, int],
        false_positive_count: int = 0,
    ) -> bool:
        """Increment statistics counters"""
        today = datetime.utcnow().date()
        total_findings = sum(findings_by_severity.values())
        
        async with self.connection_pool.acquire() as conn:
            # Get existing statistics for today
            existing = await conn.fetchrow("""
                SELECT findings_by_severity, findings_by_tool
                FROM statistics WHERE date = $1
            """, today)
            
            # Merge with existing data
            if existing:
                existing_severity = existing["findings_by_severity"] or {}
                existing_tool = existing["findings_by_tool"] or {}
                
                # Merge severity
                merged_severity = dict(existing_severity)
                for key, value in findings_by_severity.items():
                    merged_severity[key] = merged_severity.get(key, 0) + value
                
                # Merge tool
                merged_tool = dict(existing_tool)
                for key, value in findings_by_tool.items():
                    merged_tool[key] = merged_tool.get(key, 0) + value
                
                # Update
                await conn.execute("""
                    UPDATE statistics SET
                        total_scans = total_scans + 1,
                        total_findings = total_findings + $1,
                        findings_by_severity = $2::jsonb,
                        findings_by_tool = $3::jsonb,
                        false_positive_count = false_positive_count + $4
                    WHERE date = $5
                """, total_findings,
                    self._dict_to_jsonb(merged_severity),
                    self._dict_to_jsonb(merged_tool),
                    false_positive_count,
                    today)
            else:
                # Insert new
                await conn.execute("""
                    INSERT INTO statistics (date, total_scans, total_findings, findings_by_severity, findings_by_tool, false_positive_count)
                    VALUES ($1, 1, $2, $3::jsonb, $4::jsonb, $5)
                """, today, total_findings,
                    self._dict_to_jsonb(findings_by_severity),
                    self._dict_to_jsonb(findings_by_tool),
                    false_positive_count)
        
        return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        async with self.connection_pool.acquire() as conn:
            # Get aggregated totals
            totals = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(total_scans), 0) as total_scans,
                    COALESCE(SUM(total_findings), 0) as total_findings,
                    COALESCE(SUM(false_positive_count), 0) as false_positive_count
                FROM statistics
            """)
            
            if not totals or totals["total_scans"] == 0:
                return {
                    "total_scans": 0,
                    "total_findings": 0,
                    "findings_by_severity": {},
                    "findings_by_tool": {},
                    "false_positive_rate": 0.0,
                }
            
            # Aggregate findings_by_severity
            severity_rows = await conn.fetch("""
                SELECT key, SUM(value::int) as total
                FROM statistics,
                LATERAL jsonb_each_text(findings_by_severity) AS severity(key, value)
                GROUP BY key
            """)
            
            findings_by_severity = {}
            for row in severity_rows:
                findings_by_severity[row["key"]] = row["total"]
            
            # Aggregate findings_by_tool
            tool_rows = await conn.fetch("""
                SELECT key, SUM(value::int) as total
                FROM statistics,
                LATERAL jsonb_each_text(findings_by_tool) AS tool(key, value)
                GROUP BY key
            """)
            
            findings_by_tool = {}
            for row in tool_rows:
                findings_by_tool[row["key"]] = row["total"]
            
            total_findings = totals["total_findings"] or 0
            false_positive_rate = 0.0
            if total_findings > 0:
                false_positive_count = totals["false_positive_count"] or 0
                false_positive_rate = false_positive_count / total_findings
            
            return {
                "total_scans": totals["total_scans"] or 0,
                "total_findings": total_findings,
                "findings_by_severity": findings_by_severity,
                "findings_by_tool": findings_by_tool,
                "false_positive_rate": false_positive_rate,
            }
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        result = {}
        for key, value in row.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def _inject_metadata_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata JSON into top-level fields"""
        if "metadata" in result and result["metadata"]:
            try:
                import json
                metadata = json.loads(result["metadata"]) if isinstance(result["metadata"], str) else result["metadata"]
                if isinstance(metadata, dict):
                    if "selected_scanners" in metadata:
                        result["selected_scanners"] = metadata["selected_scanners"]
                    if "finding_policy" in metadata:
                        result["finding_policy"] = metadata["finding_policy"]
            except (json.JSONDecodeError, TypeError):
                pass  # Ignore if metadata is not valid JSON
        return result
    
    def _dict_to_jsonb(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to JSONB string"""
        import json
        return json.dumps(data)
