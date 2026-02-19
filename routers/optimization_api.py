"""
Optimization API Router - Phase 3C
Endpoints for performance optimization and system tuning
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from deps import get_db
from performance_optimization_service import (
    CacheOptimizationService,
    QueryOptimizationService,
    DatabaseOptimizationService
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


@router.post("/cache/enable", summary="Enable Redis Cache")
async def enable_redis_cache(
    host: str = Query("localhost", description="Redis host"),
    port: int = Query(6379, description="Redis port"),
    ttl: int = Query(3600, description="Cache TTL in seconds"),
    db: Session = Depends(get_db)
):
    """Configure and enable Redis cache"""
    try:
        config = {
            "host": host,
            "port": port,
            "ttl": ttl
        }
        
        result = await CacheOptimizationService.enable_redis_cache(db, config)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error enabling cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/warm", summary="Warm Cache")
async def warm_cache(db: Session = Depends(get_db)):
    """Pre-load popular data into cache"""
    try:
        result = await CacheOptimizationService.warm_cache(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error warming cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/performance", summary="Analyze Cache Performance")
async def analyze_cache_performance(db: Session = Depends(get_db)):
    """Analyze cache hit rates and performance metrics"""
    try:
        result = await CacheOptimizationService.analyze_cache_performance(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error analyzing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate", summary="Invalidate Cache")
async def invalidate_cache(
    pattern: Optional[str] = Query(None, description="Pattern to match for invalidation"),
    db: Session = Depends(get_db)
):
    """Clear cache entries by pattern or all"""
    try:
        result = await CacheOptimizationService.invalidate_cache(db, pattern)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/regions", summary="Optimize Region Queries")
async def optimize_region_queries(db: Session = Depends(get_db)):
    """Optimize region-related database queries"""
    try:
        result = await QueryOptimizationService.optimize_region_queries(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error optimizing region queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/currencies", summary="Optimize Currency Queries")
async def optimize_currency_queries(db: Session = Depends(get_db)):
    """Optimize currency-related database queries"""
    try:
        result = await QueryOptimizationService.optimize_currency_queries(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error optimizing currency queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/create-indexes", summary="Create Missing Indexes")
async def create_missing_indexes(db: Session = Depends(get_db)):
    """Create recommended database indexes for performance"""
    try:
        result = await DatabaseOptimizationService.add_missing_indexes(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/statistics", summary="Analyze Table Statistics")
async def analyze_table_statistics(db: Session = Depends(get_db)):
    """Analyze database table statistics and performance"""
    try:
        result = await DatabaseOptimizationService.analyze_table_statistics(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error analyzing statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/analyze-slow-queries", summary="Analyze Slow Queries")
async def analyze_slow_queries(db: Session = Depends(get_db)):
    """Identify and analyze slow running queries"""
    try:
        result = await QueryOptimizationService.analyze_slow_queries(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error analyzing slow queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
