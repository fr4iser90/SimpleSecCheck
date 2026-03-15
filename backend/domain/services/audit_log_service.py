"""
Audit Log Service

Service for logging security-relevant events to the audit log.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
import logging

from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import AuditLog
from sqlalchemy import select, desc, and_, or_, func

logger = logging.getLogger(__name__)


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
        
        Args:
            user_id: ID of the user who performed the action
            user_email: Email of the user (denormalized for deleted users)
            action_type: Type of action (USER_CREATED, FEATURE_FLAG_CHANGED, etc.)
            target: What was changed (user email, feature flag name, etc.)
            details: Additional context as dictionary
            ip_address: IP address of the request
            user_agent: User agent string
            result: Result of the action (success, failure)
        """
        try:
            async with db_adapter.async_session() as session:
                audit_entry = AuditLog(
                    user_id=UUID(user_id) if user_id else None,
                    user_email=user_email,
                    action_type=action_type,
                    target=target,
                    details=details or {},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    result=result,
                    created_at=datetime.utcnow()
                )
                session.add(audit_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
            # Don't raise - audit logging should not break the application
    
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
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            user_id: Filter by user ID
            action_type: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            search: Search in target and details
            
        Returns:
            Dictionary with 'entries' and 'total' count
        """
        try:
            async with db_adapter.async_session() as session:
                # Build query
                query = select(AuditLog)
                
                # Apply filters
                conditions = []
                if user_id:
                    conditions.append(AuditLog.user_id == UUID(user_id))
                if action_type:
                    conditions.append(AuditLog.action_type == action_type)
                if start_date:
                    conditions.append(AuditLog.created_at >= start_date)
                if end_date:
                    conditions.append(AuditLog.created_at <= end_date)
                if search:
                    conditions.append(
                        or_(
                            AuditLog.target.ilike(f"%{search}%"),
                            AuditLog.user_email.ilike(f"%{search}%")
                        )
                    )
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Get total count
                count_query = select(func.count()).select_from(AuditLog)
                if conditions:
                    count_query = count_query.where(and_(*conditions))
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0
                
                # Get entries with pagination
                query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
                result = await session.execute(query)
                entries = result.scalars().all()
                
                # Convert to dict
                audit_entries = []
                for entry in entries:
                    audit_entries.append({
                        "id": str(entry.id),
                        "user_id": str(entry.user_id) if entry.user_id else None,
                        "user_email": entry.user_email,
                        "action_type": entry.action_type,
                        "target": entry.target,
                        "details": entry.details,
                        "ip_address": str(entry.ip_address) if entry.ip_address else None,
                        "user_agent": entry.user_agent,
                        "result": entry.result,
                        "created_at": entry.created_at.isoformat()
                    })
                
                return {
                    "entries": audit_entries,
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
