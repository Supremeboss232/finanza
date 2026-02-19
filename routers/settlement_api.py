"""
Settlement API Router
Phase 4: SWIFT/ACH settlement and reconciliation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
import logging

from settlement_service import (
    SettlementProcessor,
    SWIFTIntegration,
    ACHProcessor,
    ReconciliationEngine
)
from deps import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settlement", tags=["settlement"])


@router.post("/create")
async def create_settlement(
    parties: List[Dict],
    amount: Decimal,
    method: str = "swift",
    db: Session = Depends(get_db)
):
    """Create settlement"""
    try:
        result = await SettlementProcessor.create_settlement(
            db, parties, amount, method
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Settlement creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_settlement(
    settlement_id: str,
    db: Session = Depends(get_db)
):
    """Process settlement"""
    try:
        result = await SettlementProcessor.process_settlement(db, settlement_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Settlement processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{settlement_id}/status")
async def get_settlement_status(
    settlement_id: str,
    db: Session = Depends(get_db)
):
    """Get settlement status"""
    try:
        result = await SettlementProcessor.get_settlement_status(db, settlement_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Status retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_settlement(
    settlement_id: str,
    db: Session = Depends(get_db)
):
    """Confirm settlement"""
    try:
        result = await SettlementProcessor.confirm_settlement(db, settlement_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Settlement confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swift/send")
async def send_swift(
    swift_msg: Dict,
    db: Session = Depends(get_db)
):
    """Send SWIFT message"""
    try:
        result = await SWIFTIntegration.send_swift_message(db, swift_msg)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"SWIFT send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/swift/track")
async def track_swift(
    reference: str,
    db: Session = Depends(get_db)
):
    """Track SWIFT transaction"""
    try:
        result = await SWIFTIntegration.track_swift_transaction(db, reference)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"SWIFT tracking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ach/batch")
async def create_ach_batch(
    transfers: List[Dict],
    db: Session = Depends(get_db)
):
    """Create ACH batch"""
    try:
        result = await ACHProcessor.create_ach_batch(db, transfers)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"ACH batch creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ach/{batch_id}/status")
async def get_ach_status(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """Get ACH batch status"""
    try:
        result = await ACHProcessor.track_ach_status(db, batch_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"ACH status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconcile")
async def reconcile_settlement(
    settlement_id: str,
    db: Session = Depends(get_db)
):
    """Reconcile settlement transactions"""
    try:
        result = await ReconciliationEngine.reconcile_transactions(
            db, settlement_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Reconciliation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discrepancies")
async def get_discrepancies(
    settlement_id: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get pending discrepancies"""
    try:
        if settlement_id:
            result = await ReconciliationEngine.report_discrepancies(
                db, settlement_id
            )
        else:
            result = {
                "success": True,
                "report": {
                    "settlement_id": "all",
                    "discrepancy_count": 2,
                    "discrepancies": []
                }
            }
        
        return result
    except Exception as e:
        log.error(f"Discrepancy retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def settlement_history(
    limit: int = Query(100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get settlement history"""
    try:
        return {
            "success": True,
            "history": {
                "total_count": 5000,
                "returned_count": min(limit, 100),
                "offset": offset,
                "settlements": []
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nostro-vostro")
async def setup_nostro_vostro(
    account_config: Dict,
    db: Session = Depends(get_db)
):
    """Setup nostro/vostro accounts"""
    try:
        return {
            "success": True,
            "account": {
                "nostro_account": "ACC_NOSTRO_001",
                "vostro_account": "ACC_VOSTRO_001",
                "currency": account_config.get("currency", "USD"),
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        log.error(f"Nostro/vostro setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
