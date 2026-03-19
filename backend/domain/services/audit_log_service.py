"""
Audit Log Service

Service for logging security-relevant events to the audit log.
Uses AuditLogRepository (DDD).
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from domain.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


def _get_audit_log_repository() -> AuditLogRepository:
    from infrastructure.container import get_audit_log_repository
    return get_audit_log_repository()


class AuditLogService:
    """Service for managing audit logs."""
    
    @staticmethod
    async def log_event(
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        action_type: str = "",
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "success"
    ) -> None:
        """
        Log an event to the audit log.
        """
        try:
            repo = _get_audit_log_repository()
            await repo.add(
                user_id=user_id,
                user_email=user_email,
                action_type=action_type,
                target=target,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                result=result,
            )
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
    
    @staticmethod
    async def get_audit_log(
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get audit log entries with filtering and pagination.
        """
        try:
            repo = _get_audit_log_repository()
            entries, total = await repo.get_entries(
                limit=limit,
                offset=offset,
                user_id=user_id,
                action_type=action_type,
                start_date=start_date,
                end_date=end_date,
                search=search,
            )
            return {
                "entries": entries,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def export_audit_log(
        format: str = "json",
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export audit log in specified format.
        
        Args:
            format: Export format (json, csv)
            user_id: Filter by user ID
            action_type: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Exported data as string
        """
        try:
            # Get all matching entries (no pagination for export)
            result = await AuditLogService.get_audit_log(
                limit=10000,  # Large limit for export
                offset=0,
                user_id=user_id,
                action_type=action_type,
                start_date=start_date,
                end_date=end_date
            )
            
            entries = result["entries"]
            
            if format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=[
                    "created_at", "user_email", "action_type", "target", 
                    "ip_address", "result"
                ])
                writer.writeheader()
                
                for entry in entries:
                    writer.writerow({
                        "created_at": entry["created_at"],
                        "user_email": entry["user_email"] or "",
                        "action_type": entry["action_type"],
                        "target": entry["target"] or "",
                        "ip_address": entry["ip_address"] or "",
                        "result": entry["result"]
                    })
                
                return output.getvalue()
            else:  # JSON
                import json
                return json.dumps(entries, indent=2)
        except Exception as e:
            logger.error(f"Failed to export audit log: {e}", exc_info=True)
            raise
