"""
Reporting API Router
Phase 4: Business intelligence and analytics endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict
import logging

from reporting_service import (
    ReportBuilder,
    AnalyticsEngine,
    DataVisualization,
    PredictiveAnalytics
)
from deps import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])


@router.post("/create-report")
async def create_report(
    config: Dict,
    db: Session = Depends(get_db)
):
    """Create custom report"""
    try:
        result = await ReportBuilder.create_custom_report(db, config)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Report creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}")
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Get generated report"""
    try:
        result = await ReportBuilder.generate_report(db, report_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Report retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{report_id}")
async def export_report(
    report_id: str,
    format: str = Query("csv"),
    db: Session = Depends(get_db)
):
    """Export report in format"""
    try:
        result = await ReportBuilder.export_report(db, report_id, format)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Report export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_report(
    config: Dict,
    db: Session = Depends(get_db)
):
    """Schedule automated report"""
    try:
        result = await ReportBuilder.schedule_report(db, config)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Report scheduling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/transfers")
async def analyze_transfers(
    time_period: str = Query("24h"),
    db: Session = Depends(get_db)
):
    """Analyze transfer transactions"""
    try:
        result = await AnalyticsEngine.analyze_transfers(db, time_period)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Transfer analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/users")
async def analyze_users(
    region: str = Query(None),
    db: Session = Depends(get_db)
):
    """Analyze user base"""
    try:
        filters = {"region": region} if region else {}
        result = await AnalyticsEngine.analyze_users(db, filters)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"User analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def executive_dashboard(db: Session = Depends(get_db)):
    """Get executive dashboard"""
    try:
        transfers = await AnalyticsEngine.analyze_transfers(db, "24h")
        users = await AnalyticsEngine.analyze_users(db)
        compliance = await AnalyticsEngine.analyze_compliance(db)
        
        return {
            "success": True,
            "dashboard": {
                "transfers": transfers.get("analysis"),
                "users": users.get("analysis"),
                "compliance": compliance.get("analysis")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visualization")
async def create_visualization(
    data: list,
    chart_type: str,
    db: Session = Depends(get_db)
):
    """Create data visualization"""
    try:
        result = await DataVisualization.create_chart(db, data, chart_type)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def cash_flow_forecast(
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get cash flow forecast"""
    try:
        result = await PredictiveAnalytics.forecast_cash_flow(db, days)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def analyze_trends(
    metric: str,
    period: str = Query("30d"),
    db: Session = Depends(get_db)
):
    """Analyze trends"""
    try:
        result = await PredictiveAnalytics.analyze_trends(db, metric, period)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights(
    data_type: str = Query("all"),
    db: Session = Depends(get_db)
):
    """Get business insights"""
    try:
        result = await AnalyticsEngine.generate_insights(db, data_type)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom-metric")
async def add_custom_metric(
    metric_config: Dict,
    db: Session = Depends(get_db)
):
    """Add custom metric"""
    try:
        return {
            "success": True,
            "metric_id": f"METRIC_{datetime.utcnow().timestamp()}",
            "metric_config": metric_config,
            "status": "created"
        }
    except Exception as e:
        log.error(f"Custom metric error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
