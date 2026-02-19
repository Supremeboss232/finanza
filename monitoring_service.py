"""
Monitoring Service - Phase 3C
Collects metrics and provides performance monitoring capabilities
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
from enum import Enum
import json

log = logging.getLogger(__name__)

# Metric types
class MetricType(str, Enum):
    API_CALL = "api_call"
    TRANSFER = "transfer"
    CACHE_HIT = "cache_hit"
    DB_QUERY = "db_query"
    ERROR = "error"


# In-memory metrics storage (use database in production)
METRICS_STORE = []
QUERY_PERFORMANCE_STORE = []
CACHE_PERFORMANCE_STORE = {}
TRANSFER_PERFORMANCE_STORE = []


class MetricsCollector:
    """Collects and tracks system metrics"""
    
    @staticmethod
    async def record_api_call(
        db: Session,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None
    ) -> dict:
        """Record API call metrics"""
        try:
            metric = {
                "type": MetricType.API_CALL,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "success": 200 <= status_code < 300
            }
            
            METRICS_STORE.append(metric)
            
            log.debug(f"API call recorded: {method} {endpoint} - {status_code} ({response_time_ms}ms)")
            
            return {
                "success": True,
                "data": {
                    "metric_type": "api_call",
                    "recorded_at": metric["timestamp"]
                }
            }
        except Exception as e:
            log.error(f"Error recording API call: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def record_transfer(
        db: Session,
        transfer_id: str,
        from_currency: str,
        to_currency: str,
        amount: float,
        status: str,
        processing_time_ms: float
    ) -> dict:
        """Record transfer metrics"""
        try:
            metric = {
                "type": MetricType.TRANSFER,
                "transfer_id": transfer_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "amount": amount,
                "status": status,
                "processing_time_ms": processing_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "success": status == "completed"
            }
            
            METRICS_STORE.append(metric)
            TRANSFER_PERFORMANCE_STORE.append(metric)
            
            log.info(f"Transfer recorded: {transfer_id} - {from_currency}/{to_currency} ({processing_time_ms}ms)")
            
            return {
                "success": True,
                "data": {
                    "metric_type": "transfer",
                    "transfer_id": transfer_id,
                    "recorded_at": metric["timestamp"]
                }
            }
        except Exception as e:
            log.error(f"Error recording transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def record_cache_hit(
        db: Session,
        cache_key: str,
        hit: bool,
        response_time_ms: float
    ) -> dict:
        """Record cache hit/miss"""
        try:
            metric = {
                "type": MetricType.CACHE_HIT,
                "cache_key": cache_key,
                "hit": hit,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            METRICS_STORE.append(metric)
            
            if cache_key not in CACHE_PERFORMANCE_STORE:
                CACHE_PERFORMANCE_STORE[cache_key] = {
                    "hits": 0,
                    "misses": 0,
                    "total_response_time_ms": 0,
                    "first_accessed": metric["timestamp"]
                }
            
            if hit:
                CACHE_PERFORMANCE_STORE[cache_key]["hits"] += 1
            else:
                CACHE_PERFORMANCE_STORE[cache_key]["misses"] += 1
            
            CACHE_PERFORMANCE_STORE[cache_key]["total_response_time_ms"] += response_time_ms
            CACHE_PERFORMANCE_STORE[cache_key]["last_accessed"] = metric["timestamp"]
            
            log.debug(f"Cache {'hit' if hit else 'miss'}: {cache_key} ({response_time_ms}ms)")
            
            return {
                "success": True,
                "data": {
                    "metric_type": "cache_hit",
                    "cache_key": cache_key,
                    "hit": hit,
                    "recorded_at": metric["timestamp"]
                }
            }
        except Exception as e:
            log.error(f"Error recording cache hit: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_metrics(
        db: Session,
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> dict:
        """Retrieve collected metrics"""
        try:
            metrics = METRICS_STORE.copy()
            
            # Filter by type
            if metric_type:
                metrics = [m for m in metrics if m.get("type") == metric_type]
            
            # Filter by time range
            if start_time:
                metrics = [
                    m for m in metrics
                    if datetime.fromisoformat(m["timestamp"]) >= start_time
                ]
            
            if end_time:
                metrics = [
                    m for m in metrics
                    if datetime.fromisoformat(m["timestamp"]) <= end_time
                ]
            
            # Return recent metrics
            metrics = sorted(
                metrics,
                key=lambda x: x["timestamp"],
                reverse=True
            )[:limit]
            
            return {
                "success": True,
                "data": {
                    "count": len(metrics),
                    "metric_type": metric_type,
                    "metrics": metrics
                }
            }
        except Exception as e:
            log.error(f"Error retrieving metrics: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def export_metrics(
        db: Session,
        format: str = "json",
        include_summary: bool = True
    ) -> dict:
        """Export metrics for analysis"""
        try:
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "total_metrics": len(METRICS_STORE),
                "metrics": METRICS_STORE.copy()
            }
            
            if include_summary:
                # Calculate summary statistics
                api_calls = [m for m in METRICS_STORE if m.get("type") == MetricType.API_CALL]
                transfers = [m for m in METRICS_STORE if m.get("type") == MetricType.TRANSFER]
                cache_hits = [m for m in METRICS_STORE if m.get("type") == MetricType.CACHE_HIT and m.get("hit")]
                
                export_data["summary"] = {
                    "total_api_calls": len(api_calls),
                    "total_transfers": len(transfers),
                    "total_cache_hits": len(cache_hits),
                    "avg_api_response_time_ms": round(
                        sum(m.get("response_time_ms", 0) for m in api_calls) / max(len(api_calls), 1),
                        2
                    ),
                    "successful_transfers": sum(1 for t in transfers if t.get("success")),
                    "failed_transfers": sum(1 for t in transfers if not t.get("success"))
                }
            
            log.info(f"Metrics exported: {format} format with {len(METRICS_STORE)} metrics")
            
            return {
                "success": True,
                "data": export_data
            }
        except Exception as e:
            log.error(f"Error exporting metrics: {e}")
            return {"success": False, "error": str(e)}


class PerformanceMonitor:
    """Monitors system performance"""
    
    @staticmethod
    async def monitor_query_performance(db: Session) -> dict:
        """Monitor database query performance"""
        try:
            query_stats = {
                "total_queries": len(QUERY_PERFORMANCE_STORE),
                "avg_query_time_ms": round(
                    sum(q.get("duration_ms", 0) for q in QUERY_PERFORMANCE_STORE) / 
                    max(len(QUERY_PERFORMANCE_STORE), 1),
                    2
                ),
                "slow_queries": sum(1 for q in QUERY_PERFORMANCE_STORE if q.get("duration_ms", 0) > 100),
                "slow_query_threshold_ms": 100,
                "monitoring_timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "data": query_stats
            }
        except Exception as e:
            log.error(f"Error monitoring query performance: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def monitor_cache_performance(db: Session) -> dict:
        """Monitor cache performance metrics"""
        try:
            total_accesses = 0
            total_hits = 0
            avg_response_time = 0
            
            for cache_key, stats in CACHE_PERFORMANCE_STORE.items():
                total_hits += stats["hits"]
                total_accesses += stats["hits"] + stats["misses"]
                avg_response_time += stats["total_response_time_ms"]
            
            cache_stats = {
                "total_cache_keys": len(CACHE_PERFORMANCE_STORE),
                "total_accesses": total_accesses,
                "total_hits": total_hits,
                "total_misses": total_accesses - total_hits,
                "hit_rate_percentage": round(
                    total_hits / max(total_accesses, 1) * 100,
                    2
                ),
                "avg_response_time_ms": round(
                    avg_response_time / max(total_accesses, 1),
                    2
                ),
                "monitoring_timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "data": cache_stats
            }
        except Exception as e:
            log.error(f"Error monitoring cache performance: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def monitor_transfer_performance(db: Session) -> dict:
        """Monitor transfer processing performance"""
        try:
            completed_transfers = [
                t for t in TRANSFER_PERFORMANCE_STORE
                if t.get("status") == "completed"
            ]
            
            failed_transfers = [
                t for t in TRANSFER_PERFORMANCE_STORE
                if t.get("status") != "completed"
            ]
            
            avg_processing_time = round(
                sum(t.get("processing_time_ms", 0) for t in TRANSFER_PERFORMANCE_STORE) /
                max(len(TRANSFER_PERFORMANCE_STORE), 1),
                2
            )
            
            transfer_stats = {
                "total_transfers": len(TRANSFER_PERFORMANCE_STORE),
                "completed_transfers": len(completed_transfers),
                "failed_transfers": len(failed_transfers),
                "success_rate_percentage": round(
                    len(completed_transfers) / max(len(TRANSFER_PERFORMANCE_STORE), 1) * 100,
                    2
                ),
                "avg_processing_time_ms": avg_processing_time,
                "min_processing_time_ms": min(
                    (t.get("processing_time_ms", 0) for t in TRANSFER_PERFORMANCE_STORE),
                    default=0
                ),
                "max_processing_time_ms": max(
                    (t.get("processing_time_ms", 0) for t in TRANSFER_PERFORMANCE_STORE),
                    default=0
                ),
                "monitoring_timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "data": transfer_stats
            }
        except Exception as e:
            log.error(f"Error monitoring transfer performance: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def generate_report(db: Session, report_type: str = "comprehensive") -> dict:
        """Generate comprehensive performance report"""
        try:
            api_metrics = await MetricsCollector.get_metrics(db, metric_type=MetricType.API_CALL)
            cache_metrics = await PerformanceMonitor.monitor_cache_performance(db)
            transfer_metrics = await PerformanceMonitor.monitor_transfer_performance(db)
            query_metrics = await PerformanceMonitor.monitor_query_performance(db)
            
            report = {
                "report_type": report_type,
                "generated_at": datetime.utcnow().isoformat(),
                "api_performance": api_metrics.get("data", {}),
                "cache_performance": cache_metrics.get("data", {}),
                "transfer_performance": transfer_metrics.get("data", {}),
                "database_performance": query_metrics.get("data", {}),
                "overall_health": "good" if cache_metrics["data"].get("hit_rate_percentage", 0) > 80 else "needs_attention",
                "recommendations": []
            }
            
            # Add recommendations
            if cache_metrics["data"].get("hit_rate_percentage", 0) < 80:
                report["recommendations"].append("Improve cache hit rate by warming cache with popular queries")
            
            if transfer_metrics["data"].get("success_rate_percentage", 0) < 99:
                report["recommendations"].append("Investigate transfer failures and improve reliability")
            
            if query_metrics["data"].get("slow_queries", 0) > 10:
                report["recommendations"].append("Add indexes to slow queries")
            
            log.info(f"Performance report generated: {report_type}")
            
            return {
                "success": True,
                "data": report
            }
        except Exception as e:
            log.error(f"Error generating report: {e}")
            return {"success": False, "error": str(e)}
