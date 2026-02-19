"""
Monitoring API Router - Phase 3C
Endpoints for performance monitoring and metrics collection
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from deps import get_db
from monitoring_service import MetricsCollector, PerformanceMonitor

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/metrics", summary="Get Collected Metrics")
async def get_metrics(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    limit: int = Query(100, description="Number of metrics to return"),
    db: Session = Depends(get_db)
):
    """Get collected system metrics"""
    try:
        result = await MetricsCollector.get_metrics(db, metric_type=metric_type, limit=limit)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/api-calls", summary="Get API Call Metrics")
async def get_api_call_metrics(
    limit: int = Query(50, description="Number of metrics to return"),
    db: Session = Depends(get_db)
):
    """Get API call performance metrics"""
    try:
        result = await MetricsCollector.get_metrics(
            db,
            metric_type="api_call",
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting API call metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/transfers", summary="Get Transfer Metrics")
async def get_transfer_metrics(
    limit: int = Query(50, description="Number of metrics to return"),
    db: Session = Depends(get_db)
):
    """Get transfer processing metrics"""
    try:
        result = await MetricsCollector.get_metrics(
            db,
            metric_type="transfer",
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting transfer metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/performance", summary="Get Cache Performance")
async def get_cache_performance(db: Session = Depends(get_db)):
    """Get cache hit rate and performance metrics"""
    try:
        result = await PerformanceMonitor.monitor_cache_performance(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting cache performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transfers/performance", summary="Get Transfer Performance")
async def get_transfer_performance(db: Session = Depends(get_db)):
    """Get transfer processing performance metrics"""
    try:
        result = await PerformanceMonitor.monitor_transfer_performance(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting transfer performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/performance", summary="Get Query Performance")
async def get_query_performance(db: Session = Depends(get_db)):
    """Get database query performance metrics"""
    try:
        result = await PerformanceMonitor.monitor_query_performance(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting query performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export", summary="Export Metrics")
async def export_metrics(
    format: str = Query("json", description="Export format"),
    include_summary: bool = Query(True, description="Include summary statistics"),
    db: Session = Depends(get_db)
):
    """Export collected metrics for analysis"""
    try:
        result = await MetricsCollector.export_metrics(
            db,
            format=format,
            include_summary=include_summary
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report", summary="Generate Performance Report")
async def generate_report(
    report_type: str = Query("comprehensive", description="Type of report"),
    db: Session = Depends(get_db)
):
    """Generate comprehensive performance report"""
    try:
        result = await PerformanceMonitor.generate_report(db, report_type=report_type)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="Health Check")
async def health_check(db: Session = Depends(get_db)):
    """System health check with metrics"""
    try:
        cache_perf = await PerformanceMonitor.monitor_cache_performance(db)
        transfer_perf = await PerformanceMonitor.monitor_transfer_performance(db)
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_hit_rate": cache_perf["data"].get("hit_rate_percentage", 0),
            "transfer_success_rate": transfer_perf["data"].get("success_rate_percentage", 0),
            "components": {
                "database": "operational",
                "cache": "operational",
                "api": "operational",
                "webhooks": "operational",
                "realtime": "operational"
            }
        }
        
        return health_status
    except Exception as e:
        log.error(f"Error in health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))
