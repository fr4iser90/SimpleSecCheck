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
        default="redis",
        help="Queue type (default: redis)"
    )
    
    parser.add_argument(
        "--queue-connection",
        default=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        help="Queue connection string (default: from REDIS_URL env var or redis://localhost:6379)"
    )
    
    parser.add_argument(
        "--db-connection",
        default="postgresql+asyncpg://simpleseccheck:simpleseccheck@localhost/simpleseccheck",
        help="Database connection string"
    )
    
    parser.add_argument(
        "--max-concurrent-jobs",
        type=int,
        default=3,
        help="Maximum number of concurrent jobs (default: 3)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )
    
    return parser.parse_args()


async def start_api_server():
    """Start HTTP API server for scanner discovery."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from worker.api.scanner_api import router
    
    app = FastAPI(title="SimpleSecCheck Worker API")
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router)
    
    # Run API server
    config = uvicorn.Config(app, host="0.0.0.0", port=8081, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Main entry point for the worker service."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.log_level)
    from worker.infrastructure.logging_config import get_logger
    logger = get_logger(__name__)
    
    logger.info("Worker started")
    logger.info("Queue adapter initialized", queue_type=args.queue_type)
    logger.info("Max concurrent jobs", max_jobs=args.max_concurrent_jobs)
    
    try:
        # Initialize infrastructure adapters
        docker_adapter = DockerAdapter()
        queue_adapter = QueueAdapter(args.queue_type, args.queue_connection)
        
        database_adapter = PostgreSQLAdapter(args.db_connection)
        
        # Initialize services
        docker_job_executor = DockerJobExecutor(docker_adapter)
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
            start_api_server()
        )
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())