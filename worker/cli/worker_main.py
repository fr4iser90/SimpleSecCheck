"""
Worker main CLI entrypoint.

Provides command-line interface for starting and managing the worker service.
"""

import asyncio
import logging
import sys
import argparse
import os
from pathlib import Path

# Add worker to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worker.domain.job_execution.services.job_orchestration_service import JobOrchestrationService
from worker.infrastructure.docker.docker_job_executor import DockerJobExecutor
from worker.domain.job_execution.services.result_processing_service import ResultProcessingService
from worker.infrastructure.docker_adapter import DockerAdapter
from worker.infrastructure.queue_adapter import QueueAdapter
from worker.infrastructure.database_adapter import PostgreSQLAdapter


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level
    """
    from worker.infrastructure.logging_config import setup_logging as setup_worker_logging
    setup_worker_logging()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="SimpleSecCheck Worker")
    
    parser.add_argument(
        "--queue-type",
        choices=["redis", "memory"],
        default=os.environ.get("QUEUE_TYPE"),
        help="Queue type (from QUEUE_TYPE env var)"
    )
    
    parser.add_argument(
        "--queue-connection",
        default=os.environ.get("REDIS_URL") or os.environ.get("QUEUE_CONNECTION"),
        help="Queue connection string (from REDIS_URL or QUEUE_CONNECTION env var)"
    )
    
    parser.add_argument(
        "--db-connection",
        default=os.environ.get("DATABASE_URL"),
        help="Database connection string (from DATABASE_URL env var)"
    )
    
    parser.add_argument(
        "--max-concurrent-jobs",
        type=lambda x: int(x) if x else None,
        default=os.environ.get("MAX_CONCURRENT_JOBS") or os.environ.get("WORKER_CONCURRENCY"),
        help="Maximum number of concurrent jobs (from MAX_CONCURRENT_JOBS or WORKER_CONCURRENCY env var)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.environ.get("LOG_LEVEL"),
        help="Logging level (from LOG_LEVEL env var)"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )
    
    return parser.parse_args()


async def start_api_server(database_adapter, job_orchestration_service=None):
    """Start HTTP API server for scanner discovery and jobs (cancel)."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from worker.api.scanner_api import init_router
    from worker.api.jobs_api import init_jobs_router
    
    app = FastAPI(title="SimpleSecCheck Worker API")

    # CORS: same as backend – list origins (no * with credentials). Env CORS_ORIGINS or APP_URL (e.g. from compose).
    _cors_default = "http://localhost,http://localhost:80,http://127.0.0.1,http://127.0.0.1:80"
    _cors_str = os.environ.get("CORS_ORIGINS", _cors_default)
    _cors_origins = [o.strip() for o in _cors_str.split(",") if o.strip()]
    _app_url = os.environ.get("APP_URL", "").strip().rstrip("/")
    if _app_url and _app_url not in _cors_origins:
        _cors_origins.append(_app_url)
    if not _cors_origins:
        _cors_origins = ["http://localhost", "http://localhost:80", "http://127.0.0.1", "http://127.0.0.1:80"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Scanner discovery router
    router = init_router(database_adapter)
    app.include_router(router)
    
    # Jobs router (cancel by scan_id)
    if job_orchestration_service:
        jobs_router = init_jobs_router(job_orchestration_service)
        app.include_router(jobs_router)
    
    # Run API server
    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Main entry point for the worker service."""
    args = parse_arguments()
    
    # Validate required environment variables
    if not args.queue_type:
        raise ValueError("QUEUE_TYPE environment variable is required")
    
    if not args.queue_connection:
        raise ValueError("REDIS_URL or QUEUE_CONNECTION environment variable is required")
    
    if not args.db_connection:
        raise ValueError("DATABASE_URL environment variable is required")
    
    if not args.max_concurrent_jobs:
        raise ValueError("MAX_CONCURRENT_JOBS or WORKER_CONCURRENCY environment variable is required")
    
    # Set up logging FIRST with ERROR level (will be adjusted after setup check)
    # This prevents any logs during initialization before we can check setup status
    import structlog
    logging.basicConfig(
        level=logging.ERROR,
        format="%(message)s",
        stream=sys.stdout,
    )
    # Set all loggers to ERROR level
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger("worker").setLevel(logging.ERROR)
    # Configure structlog with ERROR level to suppress INFO/DEBUG
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Set structlog level to ERROR
    structlog.get_logger().setLevel(logging.ERROR)
    
    # Initialize database adapter to check setup status
    db_url = args.db_connection
    if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    database_adapter = PostgreSQLAdapter(db_url)
    await database_adapter.initialize()
    
    # Check setup status early to configure logging
    setup_complete = False
    try:
        from sqlalchemy import text, select
        from infrastructure.database.models import SystemState, SetupStatusEnum
        
        async with database_adapter.get_session() as session:
            # Check if system_state table exists
            result = await session.execute(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": "public.system_state"}
            )
            table_exists = result.scalar() is not None
            
            if table_exists:
                result = await session.execute(select(SystemState).limit(1))
                system_state = result.scalar_one_or_none()
                if system_state:
                    setup_complete = (
                        (system_state.setup_status == SetupStatusEnum.COMPLETED or
                         system_state.setup_status == SetupStatusEnum.LOCKED) and
                        system_state.setup_locked and
                        system_state.database_initialized and
                        system_state.admin_user_created and
                        system_state.system_configured
                    )
    except Exception:
        pass  # If we can't check, assume setup is not complete
    
    # Configure logging based on setup status
    if setup_complete:
        # After setup: Normal logging - reconfigure with proper level
        setup_logging(args.log_level or "INFO")
    # If not complete, keep ERROR level (already set above)
    
    from worker.infrastructure.logging_config import get_logger
    logger = get_logger(__name__)
    
    # Only log if setup is complete
    if setup_complete:
        logger.info("Worker started")
        logger.info("Queue adapter initialized", queue_type=args.queue_type)
        logger.info("Max concurrent jobs", max_jobs=args.max_concurrent_jobs)
    
    try:
        # Initialize infrastructure adapters
        docker_adapter = DockerAdapter()
        queue_adapter = QueueAdapter(args.queue_type, args.queue_connection)
        
        # Initialize scanner API router with database adapter (needed for pre-loading)
        from worker.api.scanner_api import init_router
        init_router(database_adapter)
        
        # Pre-load scanners on worker startup (ensures they're available when backend starts)
        try:
            from worker.api.scanner_api import _ensure_scanners_loaded
            if setup_complete:
                logger.info("Pre-loading scanners on worker startup...")
            await _ensure_scanners_loaded()
            if setup_complete:
                logger.info("Scanners successfully pre-loaded")
        except Exception as e:
            if setup_complete:
                logger.warning(f"Failed to pre-load scanners on startup: {e}")
            # Don't fail startup - scanners will be loaded on first API request
        
        # Initialize services
        docker_job_executor = DockerJobExecutor(docker_adapter, database_adapter)
        result_processing_service = ResultProcessingService(database_adapter)
        job_orchestration_service = JobOrchestrationService(
            docker_job_executor,
            result_processing_service,
            queue_adapter,
            database_adapter,
            args.max_concurrent_jobs
        )
        
        # Start worker and API server in parallel
        await asyncio.gather(
            job_orchestration_service.start_worker(),
            start_api_server(database_adapter, job_orchestration_service)
        )
            
    except KeyboardInterrupt:
        if setup_complete:
            logger.info("Worker stopped by user")
    except Exception as e:
        if setup_complete:
            logger.error("Worker failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())