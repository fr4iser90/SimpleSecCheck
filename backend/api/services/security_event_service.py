"""
Security Event Service

This service handles security event logging for SIEM integration and audit trail
management with enterprise-grade security monitoring.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from config.settings import settings


class SecurityEventService:
    """Service for logging security events with SIEM integration."""
    
    def __init__(self):
        """
        Initialize SecurityEventService.
        """
        self.logger = logging.getLogger("security.events")
        self.event_types = {
            # Setup Events
            "SETUP_TOKEN_GENERATED": "CRITICAL",
            "SETUP_TOKEN_VERIFIED": "INFO",
            "SETUP_TOKEN_INVALID": "WARNING",
            "SETUP_TOKEN_EXPIRED": "WARNING",
            "SETUP_TOKEN_REPLAY_ATTEMPT": "CRITICAL",
            "SETUP_SESSION_CREATED": "INFO",
            "SETUP_SESSION_VALIDATED": "INFO",
            "SETUP_SESSION_EXPIRED": "INFO",
            "SETUP_SESSION_HIJACK_ATTEMPT": "CRITICAL",
            "SETUP_COMPLETED": "CRITICAL",
            "SETUP_LOCKED": "CRITICAL",
            "SETUP_ACCESS_AFTER_LOCK": "CRITICAL",
            "SETUP_RESET": "WARNING",
            
            # Authentication Events
            "LOGIN_SUCCESS": "INFO",
            "LOGIN_FAILED": "WARNING",
            "LOGIN_RATE_LIMITED": "WARNING",
            "PASSWORD_CHANGED": "INFO",
            "PASSWORD_RESET": "WARNING",
            
            # Security Events
            "BRUTE_FORCE_ATTEMPT": "CRITICAL",
            "IP_BANNED": "WARNING",
            "IP_UNBANNED": "INFO",
            "CSRF_TOKEN_INVALID": "WARNING",
            "UNAUTHORIZED_ACCESS": "CRITICAL",
            "PRIVILEGE_ESCALATION": "CRITICAL",
        }
    
    def log_event(self, event_type: str, details: Dict[str, Any], severity: Optional[str] = None):
        """
        Log a security event with structured data.
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
            severity: Event severity (INFO, WARNING, CRITICAL)
        """
        # Determine severity
        if severity is None:
            severity = self.event_types.get(event_type, "INFO")
        
        # Create structured event
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "source": "setup_wizard",
            "security_mode": settings.SECURITY_MODE,
            "details": details,
            "version": "1.0.0"
        }
        
        # Log with appropriate level
        if severity == "CRITICAL":
            self.logger.critical(f"Security Event: {event_type}", extra=event)
        elif severity == "WARNING":
            self.logger.warning(f"Security Event: {event_type}", extra=event)
        else:
            self.logger.info(f"Security Event: {event_type}", extra=event)
    
    def log_setup_token_generated(self, ip: str, user_agent: str, token_hash: str):
        """Log setup token generation."""
        self.log_event("SETUP_TOKEN_GENERATED", {
            "ip": ip,
            "user_agent": user_agent,
            "token_hash": token_hash,
            "action": "token_generated"
        })
    
    def log_setup_token_verified(self, ip: str, user_agent: str, admin_email: str):
        """Log successful setup token verification."""
        self.log_event("SETUP_TOKEN_VERIFIED", {
            "ip": ip,
            "user_agent": user_agent,
            "admin_email": admin_email,
            "action": "token_verified"
        })
    
    def log_setup_token_invalid(self, ip: str, user_agent: str, attempt_count: int):
        """Log invalid setup token attempt."""
        self.log_event("SETUP_TOKEN_INVALID", {
            "ip": ip,
            "user_agent": user_agent,
            "attempt_count": attempt_count,
            "action": "token_invalid"
        })
    
    def log_setup_token_expired(self, ip: str, user_agent: str, token_age_hours: float):
        """Log expired setup token attempt."""
        self.log_event("SETUP_TOKEN_EXPIRED", {
            "ip": ip,
            "user_agent": user_agent,
            "token_age_hours": token_age_hours,
            "action": "token_expired"
        })
    
    def log_setup_token_replay_attempt(self, ip: str, user_agent: str):
        """Log setup token replay attempt."""
        self.log_event("SETUP_TOKEN_REPLAY_ATTEMPT", {
            "ip": ip,
            "user_agent": user_agent,
            "action": "token_replay"
        })
    
    def log_setup_session_created(self, session_id: str, ip: str, user_agent: str):
        """Log setup session creation."""
        self.log_event("SETUP_SESSION_CREATED", {
            "session_id": session_id,
            "ip": ip,
            "user_agent": user_agent,
            "action": "session_created"
        })
    
    def log_setup_session_hijack_attempt(self, session_id: str, ip: str, user_agent: str, expected_ip: str, expected_ua: str):
        """Log setup session hijack attempt."""
        self.log_event("SETUP_SESSION_HIJACK_ATTEMPT", {
            "session_id": session_id,
            "current_ip": ip,
            "current_user_agent": user_agent,
            "expected_ip": expected_ip,
            "expected_user_agent": expected_ua,
            "action": "session_hijack_attempt"
        })
    
    def log_setup_completed(self, admin_email: str, ip: str, user_agent: str, setup_duration_minutes: float):
        """Log setup completion."""
        self.log_event("SETUP_COMPLETED", {
            "admin_email": admin_email,
            "ip": ip,
            "user_agent": user_agent,
            "setup_duration_minutes": setup_duration_minutes,
            "setup_locked": True,
            "action": "setup_completed"
        })
    
    def log_setup_locked(self, ip: str, user_agent: str):
        """Log setup lock activation."""
        self.log_event("SETUP_LOCKED", {
            "ip": ip,
            "user_agent": user_agent,
            "setup_locked": True,
            "action": "setup_locked"
        })
    
    def log_setup_access_after_lock(self, ip: str, user_agent: str, endpoint: str):
        """Log unauthorized setup access attempt after lock."""
        self.log_event("SETUP_ACCESS_AFTER_LOCK", {
            "ip": ip,
            "user_agent": user_agent,
            "endpoint": endpoint,
            "action": "unauthorized_setup_access"
        })
    
    def log_brute_force_attempt(self, ip: str, user_agent: str, attempt_count: int, time_window: str):
        """Log brute force attack attempt."""
        self.log_event("BRUTE_FORCE_ATTEMPT", {
            "ip": ip,
            "user_agent": user_agent,
            "attempt_count": attempt_count,
            "time_window": time_window,
            "action": "brute_force_detected"
        })
    
    def log_ip_banned(self, ip: str, ban_duration_minutes: int, reason: str):
        """Log IP address ban."""
        self.log_event("IP_BANNED", {
            "ip": ip,
            "ban_duration_minutes": ban_duration_minutes,
            "reason": reason,
            "action": "ip_banned"
        })
    
    def log_csrf_token_invalid(self, ip: str, user_agent: str, endpoint: str):
        """Log invalid CSRF token."""
        self.log_event("CSRF_TOKEN_INVALID", {
            "ip": ip,
            "user_agent": user_agent,
            "endpoint": endpoint,
            "action": "csrf_token_invalid"
        })
    
    def log_unauthorized_access(self, ip: str, user_agent: str, endpoint: str, auth_method: str):
        """Log unauthorized access attempt."""
        self.log_event("UNAUTHORIZED_ACCESS", {
            "ip": ip,
            "user_agent": user_agent,
            "endpoint": endpoint,
            "auth_method": auth_method,
            "action": "unauthorized_access"
        })
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get security event summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Security summary dictionary
        """
        # This would typically query a log aggregation system
        # For now, return a placeholder structure
        return {
            "time_period_hours": hours,
            "total_events": 0,
            "critical_events": 0,
            "warning_events": 0,
            "info_events": 0,
            "unique_ips": 0,
            "top_event_types": [],
            "banned_ips": [],
            "setup_attempts": 0,
            "failed_logins": 0
        }
    
    def export_security_events(self, start_time: datetime, end_time: datetime, format: str = "json") -> str:
        """
        Export security events for the specified time period.
        
        Args:
            start_time: Start time for export
            end_time: End time for export
            format: Export format (json, csv)
            
        Returns:
            Exported events as string
        """
        # This would typically query a log aggregation system
        # For now, return a placeholder
        export_data = {
            "export_time": datetime.utcnow().isoformat(),
            "time_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "format": format,
            "events": [],
            "total_count": 0
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            return str(export_data)