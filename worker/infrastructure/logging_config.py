"""
Logging Configuration for Worker Service

This module sets up structured logging for the worker service with clean output format.
"""
import structlog
import logging
import sys
import os
from typing import Any, Dict

# Get settings from environment variables (worker doesn't have config module)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")


def setup_logging():
    """Configure structured logging for worker."""
    # Configure structlog processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if LOG_FORMAT == "json":
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
        level=getattr(logging, LOG_LEVEL.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Set Docker adapter log level to DEBUG to reduce verbosity
    logging.getLogger("worker.infrastructure.docker_adapter").setLevel(logging.DEBUG)
    
    # Apply clean format to all worker loggers
    for name in logging.root.manager.loggerDict.keys():
        if name.startswith('worker'):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.setFormatter(structlog.dev.ConsoleRenderer())


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def log_worker_start(logger: structlog.BoundLogger, max_jobs: int):
    """Log worker startup."""
    logger.info("[Worker] Starting SimpleSecCheck Worker")
    logger.info(f"[Worker] Max concurrent jobs: {max_jobs}")


def log_queue_config(logger: structlog.BoundLogger, queue_type: str):
    """Log queue configuration."""
    logger.info(f"[Worker] Queue type: {queue_type}")


def log_job_start(logger: structlog.BoundLogger, job_id: str):
    """Log job start."""
    logger.info(f"[Worker] Starting job: {job_id}")


def log_job_complete(logger: structlog.BoundLogger, job_id: str, duration: float):
    """Log job completion."""
    logger.info(f"[Worker] Job completed: {job_id} (duration: {duration}s)")


def log_critical_warning(logger: structlog.BoundLogger, message: str):
    """Log critical warnings."""
    logger.warning(f"[Worker] {message}")


def log_error(logger: structlog.BoundLogger, error: str):
    """Log errors."""
    logger.error(f"[Worker] {error}")
