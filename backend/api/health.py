"""
Health Check Endpoints

This module provides health check endpoints for monitoring the backend service.
"""
from fastapi import APIRouter, HTTPException, Response
from typing import Dict, Any

from infrastructure.container import get_database_health
from infrastructure.redis.client import get_redis_health

router = APIRouter()

@router.get("/health")
async def health():
    """Basic health check endpoint."""
    return Response(status_code=200)

@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    """Detailed health check including dependencies."""
    health_status = {
        "status": "healthy",
        "service": "backend",
        "version": "1.0.0",
        "dependencies": {}
    }
    
    # Check database health
    try:
        db_health = await get_database_health()
        health_status["dependencies"]["database"] = db_health
        if not db_health["status"]:
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["dependencies"]["database"] = {
            "status": False,
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Redis health
    try:
        redis_health = await get_redis_health()
        health_status["dependencies"]["redis"] = redis_health
        if not redis_health["status"]:
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["dependencies"]["redis"] = {
            "status": False,
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/health/database", response_model=Dict[str, Any])
async def database_health():
    """Database-specific health check."""
    try:
        health = await get_database_health()
        if not health["status"]:
            raise HTTPException(status_code=503, detail="Database unhealthy")
        return health
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database check failed: {str(e)}")

@router.get("/health/redis", response_model=Dict[str, Any])
async def redis_health():
    """Redis-specific health check."""
    try:
        health = await get_redis_health()
        if not health["status"]:
            raise HTTPException(status_code=503, detail="Redis unhealthy")
        return health
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis check failed: {str(e)}")

@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Readiness check for Kubernetes."""
    # Check if all dependencies are ready
    try:
        db_health = await get_database_health()
        redis_health = await get_redis_health()
        
        if db_health["status"] and redis_health["status"]:
            return {"status": "ready", "message": "Service is ready to handle requests"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")

@router.get("/live", response_model=Dict[str, Any])
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive", "message": "Service is running"}
