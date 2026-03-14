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
        """Update scan status in database.
        
        Args:
            result: Execution result
        """
        try:
            # This would update the scan status in the database
            # Implementation depends on database schema
            pass
            
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