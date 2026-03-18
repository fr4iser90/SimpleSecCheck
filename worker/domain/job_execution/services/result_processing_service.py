"""
Result processing service for the worker domain.

Handles the processing and storage of execution results including findings and reports.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from uuid import UUID

from worker.domain.job_execution.entities.execution_result import ExecutionResult
from worker.infrastructure.database_adapter import PostgreSQLAdapter


def _normalize_severity(severity: Any) -> str:
    """Map severity string to canonical: critical, high, medium, low, info."""
    if severity is None:
        return "info"
    s = str(severity).strip().upper()
    if not s:
        return "info"
    if s in ("CRITICAL", "CRIT"):
        return "critical"
    if s == "HIGH":
        return "high"
    if s in ("MEDIUM", "MODERATE"):
        return "medium"
    if s == "LOW":
        return "low"
    if s in ("INFO", "INFORMATIONAL", "NOTE"):
        return "info"
    return "info"


def _build_scan_results_for_duration_stats(structured_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build list of {scanner, duration} for DB results and scanner_duration_stats.
    Uses _steps from steps.log (started_at/completed_at) when present; else tries duration from tool reports.
    """
    out: List[Dict[str, Any]] = []
    # Prefer steps.log: one JSON object per step with name, started_at, completed_at
    steps = structured_results.get("_steps") or []
    for step in steps:
        if not isinstance(step, dict):
            continue
        name = step.get("name")
        started = step.get("started_at")
        completed = step.get("completed_at")
        if not name or not started or not completed:
            continue
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00")) if isinstance(started, str) else None
            end_dt = datetime.fromisoformat(completed.replace("Z", "+00:00")) if isinstance(completed, str) else None
            if start_dt and end_dt and end_dt >= start_dt:
                sec = int((end_dt - start_dt).total_seconds())
                if sec > 0:
                    out.append({"scanner": name, "duration": sec})
        except Exception:
            continue
    if out:
        return out
    # Fallback: tool report may have "duration" or "execution_time_seconds"
    for key, value in structured_results.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, dict):
            continue
        duration = value.get("duration") or value.get("execution_time_seconds")
        if duration is not None:
            try:
                sec = int(float(duration))
                if sec > 0:
                    out.append({"scanner": key, "duration": sec})
            except (TypeError, ValueError):
                continue
    return out


def _aggregate_vulnerability_counts(structured_results: Dict[str, Any]) -> Dict[str, int]:
    """
    Aggregate total and per-severity counts from all tools in structured_results.
    Each tool report may have 'vulnerabilities', 'findings', or a list; items have 'severity' or 'Severity'.
    Returns dict with keys: total_vulnerabilities, critical_vulnerabilities, high_vulnerabilities,
    medium_vulnerabilities, low_vulnerabilities, info_vulnerabilities.
    """
    counts = {
        "total_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "high_vulnerabilities": 0,
        "medium_vulnerabilities": 0,
        "low_vulnerabilities": 0,
        "info_vulnerabilities": 0,
    }
    if not structured_results:
        return counts

    for _tool_name, tool_data in structured_results.items():
        if isinstance(tool_data, list):
            items = tool_data
        elif isinstance(tool_data, dict):
            items = (
                tool_data.get("vulnerabilities")
                or tool_data.get("findings")
                or tool_data.get("results")
                or []
            )
            # Trivy format: {"Results": [{"Vulnerabilities": [...]}]}
            if not items and "Results" in tool_data:
                for entry in tool_data.get("Results") or []:
                    if isinstance(entry, dict):
                        vulns = entry.get("Vulnerabilities") or entry.get("vulnerabilities") or []
                        if isinstance(vulns, list):
                            items = items + vulns
        else:
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            sev = (
                item.get("severity")
                or item.get("Severity")
                or item.get("issue_severity")
                or (item.get("extra") or {}).get("severity")
            )
            canonical = _normalize_severity(sev)
            counts["total_vulnerabilities"] += 1
            if canonical == "critical":
                counts["critical_vulnerabilities"] += 1
            elif canonical == "high":
                counts["high_vulnerabilities"] += 1
            elif canonical == "medium":
                counts["medium_vulnerabilities"] += 1
            elif canonical == "low":
                counts["low_vulnerabilities"] += 1
            else:
                counts["info_vulnerabilities"] += 1

    return counts


async def update_scan_status_to_running(database_adapter: PostgreSQLAdapter, scan_id: str) -> None:
    """Update scan status to running in database.
    
    Args:
        database_adapter: Database adapter
        scan_id: Scan ID
    """
    try:
        from sqlalchemy import text
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Update scan status to running
        async with database_adapter.get_session() as session:
            now = datetime.utcnow()
            update_query = text("""
                UPDATE scans 
                SET status = :status,
                    started_at = :started_at,
                    updated_at = :updated_at,
                    last_heartbeat_at = :heartbeat
                WHERE id = :scan_id
            """)
            
            await session.execute(
                update_query,
                {
                    "scan_id": scan_id,
                    "status": "running",
                    "started_at": now,
                    "updated_at": now,
                    "heartbeat": now,
                }
            )
            await session.commit()
            
            logger.info(f"Updated scan {scan_id} status to running")
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating scan status to running: {e}")
        # Don't raise - this is not critical for job execution


async def update_scan_heartbeat(database_adapter: PostgreSQLAdapter, scan_id: str) -> None:
    """Periodic liveness ping while worker runs the scan container."""
    try:
        from sqlalchemy import text
        from datetime import datetime

        now = datetime.utcnow()
        async with database_adapter.get_session() as session:
            await session.execute(
                text("""
                    UPDATE scans
                    SET last_heartbeat_at = :hb, updated_at = :hb
                    WHERE id = :scan_id AND status = 'running'
                """),
                {"scan_id": scan_id, "hb": now},
            )
            await session.commit()
    except Exception:
        pass


class ResultProcessingService:
    """Service for processing execution results."""
    
    def __init__(self, database_adapter: PostgreSQLAdapter):
        """Initialize the result processing service.
        
        Args:
            database_adapter: Database adapter for result storage
        """
        self.database_adapter = database_adapter
        self.logger = logging.getLogger(__name__)
    
    async def process_execution_result(self, result: ExecutionResult) -> bool:
        """Process an execution result.
        
        Args:
            result: Execution result to process
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Save structured results
            await self._save_structured_results(result)
            
            # Save file results
            await self._save_file_results(result)
            
            # Update scan status
            await self._update_scan_status(result)
            
            # Generate summary
            await self._generate_execution_summary(result)
            
            self.logger.info(f"Processed execution result for scan {result.scan_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing execution result: {e}")
            return False
    
    async def _save_structured_results(self, result: ExecutionResult) -> None:
        """Save structured results to database.
        
        Args:
            result: Execution result
        """
        try:
            # Save findings
            findings = result.structured_results.get("findings", [])
            if findings:
                await self._save_findings(result.scan_id, findings)
            
            # Save vulnerabilities
            vulnerabilities = result.structured_results.get("vulnerabilities", [])
            if vulnerabilities:
                await self._save_vulnerabilities(result.scan_id, vulnerabilities)
            
            # Save summary
            summary = result.structured_results.get("summary", {})
            if summary:
                await self._save_summary(result.scan_id, summary)
            
        except Exception as e:
            self.logger.error(f"Error saving structured results: {e}")
            raise
    
    async def _save_file_results(self, result: ExecutionResult) -> None:
        """Save file results to database.
        
        Args:
            result: Execution result
        """
        try:
            for file_path, content in result.file_results.items():
                await self._save_file_result(result.scan_id, file_path, content)
                
        except Exception as e:
            self.logger.error(f"Error saving file results: {e}")
            raise
    
    async def _save_findings(self, scan_id: UUID, findings: List[Dict[str, Any]]) -> None:
        """Save findings to database.
        
        Args:
            scan_id: Scan ID
            findings: List of findings
        """
        try:
            # This would insert findings into the database
            # Implementation depends on database schema
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving findings: {e}")
            raise
    
    async def _save_vulnerabilities(self, scan_id: UUID, vulnerabilities: List[Dict[str, Any]]) -> None:
        """Save vulnerabilities to database.
        
        Args:
            scan_id: Scan ID
            vulnerabilities: List of vulnerabilities
        """
        try:
            # This would insert vulnerabilities into the database
            # Implementation depends on database schema
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving vulnerabilities: {e}")
            raise
    
    async def _save_summary(self, scan_id: UUID, summary: Dict[str, Any]) -> None:
        """Save summary to database.
        
        Args:
            scan_id: Scan ID
            summary: Summary data
        """
        try:
            # This would update the scan summary in the database
            # Implementation depends on database schema
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving summary: {e}")
            raise
    
    async def _save_file_result(self, scan_id: UUID, file_path: str, content: str) -> None:
        """Save file result to database.
        
        Args:
            scan_id: Scan ID
            file_path: File path
            content: File content
        """
        try:
            # This would save the file result to the database
            # Implementation depends on database schema
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving file result: {e}")
            raise
    
    async def _update_scan_status(self, result: ExecutionResult) -> None:
        """Update scan status and vulnerability statistics in database.
        
        Args:
            result: Execution result
        """
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            scan_id = str(result.scan_id)
            
            # Determine status based on execution result
            if result.success:
                status = "completed"
            else:
                status = "failed"
            
            # Use post-policy statistics when available (finding policy respected; false positives not counted)
            # Otherwise aggregate from raw tool results
            if result.structured_results.get("_post_policy_statistics"):
                vuln_counts = dict(result.structured_results["_post_policy_statistics"])
                for k in ("total_vulnerabilities", "critical_vulnerabilities", "high_vulnerabilities",
                          "medium_vulnerabilities", "low_vulnerabilities", "info_vulnerabilities"):
                    if k not in vuln_counts:
                        vuln_counts[k] = 0
            else:
                vuln_counts = _aggregate_vulnerability_counts(result.structured_results)

            # Build per-tool results for results column and scanner_duration_stats (from steps.log or tool reports)
            scan_results = _build_scan_results_for_duration_stats(result.structured_results)
            results_json = json.dumps(scan_results) if scan_results else None

            # Duration: use execution_time_seconds when set; otherwise sum of per-tool durations so DB always has a value
            if result.execution_time_seconds is not None:
                duration_seconds = int(result.execution_time_seconds)
            elif scan_results:
                duration_seconds = sum(s.get("duration", 0) or 0 for s in scan_results)
            else:
                duration_seconds = None
            
            # Update scan status, vulnerability counts, and results in database
            async with self.database_adapter.get_session() as session:
                update_query = text("""
                    UPDATE scans 
                    SET status = :status,
                        completed_at = :completed_at,
                        updated_at = :updated_at,
                        error_message = :error_message,
                        total_vulnerabilities = :total_vulnerabilities,
                        critical_vulnerabilities = :critical_vulnerabilities,
                        high_vulnerabilities = :high_vulnerabilities,
                        medium_vulnerabilities = :medium_vulnerabilities,
                        low_vulnerabilities = :low_vulnerabilities,
                        info_vulnerabilities = :info_vulnerabilities,
                        duration = :duration,
                        results = CAST(:results AS jsonb)
                    WHERE id = :scan_id
                """)
                
                await session.execute(
                    update_query,
                    {
                        "scan_id": scan_id,
                        "status": status,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "error_message": result.error_message,
                        "total_vulnerabilities": vuln_counts["total_vulnerabilities"],
                        "critical_vulnerabilities": vuln_counts["critical_vulnerabilities"],
                        "high_vulnerabilities": vuln_counts["high_vulnerabilities"],
                        "medium_vulnerabilities": vuln_counts["medium_vulnerabilities"],
                        "low_vulnerabilities": vuln_counts["low_vulnerabilities"],
                        "info_vulnerabilities": vuln_counts["info_vulnerabilities"],
                        "duration": duration_seconds,
                        "results": results_json,
                    }
                )
                await session.commit()

                # Update scanner_duration_stats (per-tool) so admin "Tool duration" and queue estimates get real data
                if scan_results:
                    try:
                        now = datetime.utcnow()
                        for item in scan_results:
                            scanner_name = item.get("scanner")
                            duration_sec = item.get("duration")
                            if not scanner_name or not duration_sec or duration_sec <= 0:
                                continue
                            upsert_sql = text("""
                                INSERT INTO scanner_duration_stats
                                    (scanner_name, avg_duration_seconds, min_duration_seconds, max_duration_seconds, sample_count, last_updated)
                                VALUES (:scanner_name, :duration_seconds, :duration_seconds, :duration_seconds, 1, :last_updated)
                                ON CONFLICT (scanner_name) DO UPDATE SET
                                    avg_duration_seconds = (scanner_duration_stats.avg_duration_seconds * scanner_duration_stats.sample_count + :duration_seconds) / (scanner_duration_stats.sample_count + 1),
                                    sample_count = scanner_duration_stats.sample_count + 1,
                                    min_duration_seconds = LEAST(COALESCE(scanner_duration_stats.min_duration_seconds, 999999), :duration_seconds),
                                    max_duration_seconds = GREATEST(COALESCE(scanner_duration_stats.max_duration_seconds, 0), :duration_seconds),
                                    last_updated = :last_updated
                            """)
                            await session.execute(
                                upsert_sql,
                                {
                                    "scanner_name": scanner_name,
                                    "duration_seconds": duration_sec,
                                    "last_updated": now,
                                }
                            )
                        await session.commit()
                        self.logger.info(f"Updated scanner_duration_stats for {len(scan_results)} tool(s) from scan {scan_id}")
                    except Exception as stats_err:
                        self.logger.warning(f"Failed to update scanner_duration_stats: {stats_err}")
                
                self.logger.info(
                    f"Updated scan {scan_id} status to {status} "
                    f"(total_vuln={vuln_counts['total_vulnerabilities']}, duration={duration_seconds}s)"
                )
            
        except Exception as e:
            self.logger.error(f"Error updating scan status: {e}")
            raise
    
    async def _generate_execution_summary(self, result: ExecutionResult) -> Dict[str, Any]:
        """Generate execution summary.
        
        Args:
            result: Execution result
            
        Returns:
            Execution summary
        """
        try:
            summary = {
                "scan_id": str(result.scan_id),
                "job_execution_id": str(result.job_execution_id),
                "success": result.success,
                "error_message": result.error_message,
                "execution_time_seconds": result.execution_time_seconds,
                "container_logs_count": len(result.container_logs),
                "structured_results_count": len(result.structured_results),
                "file_results_count": len(result.file_results),
                "has_findings": result.has_findings,
                "finding_count": result.finding_count,
                "severity_breakdown": result.severity_breakdown,
                "metadata": result.metadata,
                "created_at": result.created_at.isoformat()
            }
            
            # Save summary to database
            await self._save_execution_summary(result.scan_id, summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating execution summary: {e}")
            raise
    
    async def _save_execution_summary(self, scan_id: UUID, summary: Dict[str, Any]) -> None:
        """Save execution summary to database.
        
        Args:
            scan_id: Scan ID
            summary: Execution summary
        """
        try:
            # This would save the execution summary to the database
            # Implementation depends on database schema
            pass
            
        except Exception as e:
            self.logger.error(f"Error saving execution summary: {e}")
            raise
    
    async def get_execution_results(self, scan_id: UUID) -> Optional[Dict[str, Any]]:
        """Get execution results for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Execution results
        """
        try:
            # This would query the database for execution results
            # Implementation depends on database schema
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting execution results: {e}")
            return None
    
    async def get_execution_summary(self, scan_id: UUID) -> Optional[Dict[str, Any]]:
        """Get execution summary for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Execution summary
        """
        try:
            # This would query the database for execution summary
            # Implementation depends on database schema
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting execution summary: {e}")
            return None
    
    async def cleanup_old_results(self, max_age_days: int = 30) -> int:
        """Clean up old execution results.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of results cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            # This would delete old results from the database
            # Implementation depends on database schema
            cleaned_count = 0
            
            self.logger.info(f"Cleaned up {cleaned_count} old execution results")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old results: {e}")
            return 0