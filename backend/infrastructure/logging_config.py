"""
Logging Configuration

This module sets up structured logging for the refactored backend using structlog.
"""
import structlog
import logging
import sys
from typing import Any, Dict
from config.settings import get_settings

settings = get_settings()


def setup_logging():
    """Configure structured logging."""
    # Configure structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging with clean format
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Set Uvicorn log level to WARNING to reduce verbosity
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # Silence HTTP client debug logs (httpx/httpcore)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Apply clean format to all backend loggers
    for name in logging.root.manager.loggerDict.keys():
        if name.startswith('backend'):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.setFormatter(structlog.dev.ConsoleRenderer())


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def log_request_info(logger: structlog.BoundLogger, request_data: Dict[str, Any]):
    """Log request information."""
    logger.info(
        "request_received",
        method=request_data.get("method"),
        path=request_data.get("path"),
        user_agent=request_data.get("user_agent"),
        client_ip=request_data.get("client_ip"),
    )


def log_scan_start(logger: structlog.BoundLogger, scan_id: str, target: str):
    """Log scan start."""
    logger.info(
        "scan_started",
        scan_id=scan_id,
        target=target,
    )


def log_scan_complete(logger: structlog.BoundLogger, scan_id: str, duration: float):
    """Log scan completion."""
    logger.info(
        "scan_completed",
        scan_id=scan_id,
        duration=duration,
    )


def log_scan_error(logger: structlog.BoundLogger, scan_id: str, error: str):
    """Log scan error."""
    logger.error(
        "scan_error",
        scan_id=scan_id,
        error=error,
    )


def log_database_operation(logger: structlog.BoundLogger, operation: str, table: str, success: bool):
    """Log database operations."""
    logger.info(
        "database_operation",
        operation=operation,
        table=table,
        success=success,
    )


def log_redis_operation(logger: structlog.BoundLogger, operation: str, key: str, success: bool):
    """Log Redis operations."""
    logger.info(
        "redis_operation",
        operation=operation,
        key=key,
        success=success,
    )


def log_docker_operation(logger: structlog.BoundLogger, operation: str, container_name: str, success: bool):
    """Log Docker operations."""
    logger.info(
        "docker_operation",
        operation=operation,
        container_name=container_name,
        success=success,
    )