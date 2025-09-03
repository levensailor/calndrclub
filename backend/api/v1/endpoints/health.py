"""
Health Check Endpoints
Monitor database connectivity and system health
"""

import logging
from fastapi import APIRouter, HTTPException
from core.database import database
from core.logging import logger

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    return {"status": "healthy", "message": "Service is running"}

@router.get("/health/db")
async def database_health_check():
    """
    Database connectivity health check
    """
    try:
        # Test database connection with a simple query
        result = await database.fetch_val("SELECT 1")
        if result == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "message": "Database connection is working"
            }
        else:
            raise HTTPException(status_code=503, detail="Database health check failed")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"Database connection failed: {str(e)}"
        )

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with database pool status
    """
    try:
        # Test database connection
        result = await database.fetch_val("SELECT 1")
        
        # Get database pool information if available
        pool_info = {
            "connected": result == 1,
            "pool_size": getattr(database, '_pool', {}).get('size', 'unknown'),
            "available_connections": getattr(database, '_pool', {}).get('available', 'unknown')
        }
        
        return {
            "status": "healthy" if result == 1 else "unhealthy",
            "database": pool_info,
            "message": "Detailed health check completed"
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": {"error": str(e)},
            "message": "Health check failed"
        } 