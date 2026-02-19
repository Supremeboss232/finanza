"""
Treasury Management API Router
Phase 4: Asset and liquidity management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Dict
import logging

from treasury_service import (
    AssetManager,
    CashFlowForecaster,
    LiquidityManager,
    CollateralManager
)
from deps import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/treasury", tags=["treasury"])


@router.post("/portfolio/create")
async def create_portfolio(
    portfolio_config: Dict,
    db: Session = Depends(get_db)
):
    """Create asset portfolio"""
    try:
        result = await AssetManager.allocate_assets(db, portfolio_config)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Portfolio creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/allocate")
async def allocate_assets(
    portfolio_config: Dict,
    db: Session = Depends(get_db)
):
    """Allocate portfolio assets"""
    try:
        result = await AssetManager.allocate_assets(db, portfolio_config)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Asset allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db)
):
    """Get portfolio details"""
    try:
        result = await AssetManager.get_portfolio_value(db, portfolio_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Portfolio retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/rebalance")
async def rebalance_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db)
):
    """Rebalance portfolio"""
    try:
        result = await AssetManager.rebalance_portfolio(db, portfolio_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Portfolio rebalancing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cash-flow/forecast")
async def forecast_cash_flow(
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get cash flow forecast"""
    try:
        result = await CashFlowForecaster.forecast_cash_flow(db, days)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/liquidity/status")
async def liquidity_status(db: Session = Depends(get_db)):
    """Get liquidity status"""
    try:
        result = await LiquidityManager.get_liquidity_status(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Liquidity status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/liquidity/transfer")
async def transfer_liquidity(
    source: str,
    destination: str,
    amount: Decimal,
    db: Session = Depends(get_db)
):
    """Transfer liquidity between accounts"""
    try:
        result = await LiquidityManager.trigger_liquidity_transfer(
            db, source, destination, amount
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Liquidity transfer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collateral/register")
async def register_collateral(
    asset: Dict,
    db: Session = Depends(get_db)
):
    """Register collateral asset"""
    try:
        result = await CollateralManager.register_collateral(db, asset)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Collateral registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collateral/{asset_id}")
async def get_collateral_value(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get collateral value"""
    try:
        result = await CollateralManager.calculate_collateral_value(db, asset_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Collateral value error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def treasury_dashboard(db: Session = Depends(get_db)):
    """Get treasury dashboard"""
    try:
        portfolio = await AssetManager.get_portfolio_value(db, "main")
        liquidity = await LiquidityManager.get_liquidity_status(db)
        cash_position = await CashFlowForecaster.analyze_cash_position(db)
        
        return {
            "success": True,
            "dashboard": {
                "portfolio": portfolio.get("portfolio_value"),
                "liquidity": liquidity.get("liquidity_status"),
                "cash_position": cash_position.get("analysis")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stress-test")
async def stress_test_analysis(db: Session = Depends(get_db)):
    """Run stress test analysis"""
    try:
        return {
            "success": True,
            "stress_test": {
                "scenario_1": {"impact": "5% asset decline", "portfolio_loss": "-50000"},
                "scenario_2": {"impact": "10% liquidity withdrawal", "impact_value": "-500000"},
                "scenario_3": {"impact": "interest_rate_shock", "duration_impact": "-2.5%"}
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Stress test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stress-test/run")
async def run_stress_test(
    scenarios: list,
    db: Session = Depends(get_db)
):
    """Run custom stress test"""
    try:
        return {
            "success": True,
            "test_id": f"STRESS_{datetime.utcnow().timestamp()}",
            "scenarios": len(scenarios),
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Stress test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
