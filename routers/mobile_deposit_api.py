# routers/mobile_deposit_api.py
# API endpoints for mobile check deposit service

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from database import get_db
from models import Account, MobileDeposit
from mobile_check_deposit_service import (
    MobileDepositService,
    CheckProcessingService,
    DepositStatusService,
    QualityCheckService
)
from audit_service import AuditService

router = APIRouter(prefix="/api/v1/mobile-deposit", tags=["Mobile Deposit"])
log = logging.getLogger(__name__)


# ==================== DEPOSIT INITIATION ====================

@router.post("/initiate")
async def initiate_deposit(
    account_id: int = Query(..., gt=0),
    check_amount: float = Query(..., gt=0),
    check_number: str = Query(...),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Initiate a new mobile check deposit
    Returns session token for image uploads
    """
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        result = await MobileDepositService.initiate_deposit(
            db=db,
            account_id=account_id,
            check_amount=check_amount,
            check_number=check_number,
            created_by=current_user_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="MOBILE_DEPOSIT_INITIATED",
                entity_type="MobileDeposit",
                entity_id=result["deposit_id"],
                actor_id=current_user_id,
                details=f"Initiated deposit of ${check_amount}"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error initiating deposit: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate deposit")


# ==================== IMAGE UPLOAD ENDPOINTS ====================

@router.post("/upload/{deposit_id}/front")
async def upload_check_front(
    deposit_id: int = Query(..., gt=0),
    file: UploadFile = File(...),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Upload front side of check image"""
    try:
        # Read image file
        contents = await file.read()
        
        # Validate file size (max 5MB)
        if len(contents) > 5000000:
            raise HTTPException(status_code=400, detail="Image file too large (max 5MB)")
        
        # Validate image type
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image format (JPEG, PNG, WebP only)")
        
        result = await MobileDepositService.upload_check_front(
            db=db,
            deposit_id=deposit_id,
            image_data=contents,
            image_type="front"
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="CHECK_IMAGE_UPLOADED",
                entity_type="CheckImage",
                entity_id=result["image_id"],
                actor_id=current_user_id,
                details="Uploaded front image"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error uploading front image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")


@router.post("/upload/{deposit_id}/back")
async def upload_check_back(
    deposit_id: int = Query(..., gt=0),
    file: UploadFile = File(...),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Upload back side of check image"""
    try:
        # Read image file
        contents = await file.read()
        
        # Validate file size (max 5MB)
        if len(contents) > 5000000:
            raise HTTPException(status_code=400, detail="Image file too large (max 5MB)")
        
        # Validate image type
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image format (JPEG, PNG, WebP only)")
        
        result = await MobileDepositService.upload_check_front(
            db=db,
            deposit_id=deposit_id,
            image_data=contents,
            image_type="back"
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="CHECK_IMAGE_UPLOADED",
                entity_type="CheckImage",
                entity_id=result["image_id"],
                actor_id=current_user_id,
                details="Uploaded back image"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error uploading back image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")


# ==================== VERIFICATION & QUALITY CHECK ====================

@router.post("/{deposit_id}/verify")
async def verify_check_images(
    deposit_id: int = Query(..., gt=0),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Verify check images and extract OCR data"""
    try:
        # Check image quality first
        quality_result = await QualityCheckService.check_image_quality(
            db=db,
            deposit_id=deposit_id
        )
        
        if not quality_result["success"]:
            raise HTTPException(status_code=400, detail="Image quality check failed")
        
        if not quality_result["acceptable"]:
            await QualityCheckService.flag_suspicious(
                db=db,
                deposit_id=deposit_id,
                reason="Image quality below acceptable threshold"
            )
            return {
                "success": False,
                "error": "Image quality issue",
                "quality_score": quality_result["quality_score"],
                "issues": quality_result["issues"]
            }
        
        # Verify endorsement
        endorsement_result = await QualityCheckService.verify_endorsement(
            db=db,
            deposit_id=deposit_id
        )
        
        if not endorsement_result["endorsed"]:
            return {
                "success": False,
                "error": "Check not properly endorsed",
                "issues": endorsement_result["issues"]
            }
        
        # Read check details via OCR
        ocr_result = await CheckProcessingService.read_check_details(
            db=db,
            deposit_id=deposit_id
        )
        
        if ocr_result["success"]:
            # Validate check details
            validation_result = await CheckProcessingService.validate_check(
                db=db,
                deposit_id=deposit_id
            )
            
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="CHECK_VERIFIED",
                entity_type="MobileDeposit",
                entity_id=deposit_id,
                actor_id=current_user_id,
                details="Check images verified and OCR completed"
            )
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "quality_score": quality_result["quality_score"],
                "ocr_data": ocr_result,
                "validation": validation_result
            }
        else:
            raise HTTPException(status_code=400, detail=ocr_result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error verifying check: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify check")


@router.post("/{deposit_id}/submit")
async def submit_deposit(
    deposit_id: int = Query(..., gt=0),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Submit deposit for processing after verification"""
    try:
        # Perform fraud detection first
        fraud_result = await CheckProcessingService.detect_fraud(
            db=db,
            deposit_id=deposit_id
        )
        
        if fraud_result["success"]:
            if fraud_result["risk_level"] == "high":
                # Flag for manual review
                await QualityCheckService.flag_suspicious(
                    db=db,
                    deposit_id=deposit_id,
                    reason=f"Fraud risk: {', '.join(fraud_result['flags'])}"
                )
                return {
                    "success": False,
                    "error": "Deposit flagged for review",
                    "risk_level": fraud_result["risk_level"],
                    "flags": fraud_result["flags"]
                }
        
        # Submit deposit
        result = await MobileDepositService.submit_deposit(
            db=db,
            deposit_id=deposit_id
        )
        
        if result["success"]:
            # Create deposit hold based on amount
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            from models import DepositHold
            
            # Rules: Up to $100 immediate, rest held for standard processing
            if deposit.check_amount <= 100:
                hold_until = datetime.utcnow()  # No hold
            else:
                hold_until = datetime.utcnow() + timedelta(days=1)  # 1 business day hold
            
            hold = DepositHold(
                account_id=deposit.account_id,
                deposit_id=deposit_id,
                hold_amount=max(0, deposit.check_amount - 100),  # Hold amount above $100
                hold_until=hold_until,
                hold_reason="standard_processing"
            )
            
            db.add(hold)
            db.commit()
            
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="DEPOSIT_SUBMITTED",
                entity_type="MobileDeposit",
                entity_id=deposit_id,
                actor_id=current_user_id,
                details=f"Submitted ${deposit.check_amount} check deposit"
            )
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": "submitted",
                "amount": deposit.check_amount,
                "immediate_available": min(100, deposit.check_amount),
                "hold_amount": max(0, deposit.check_amount - 100),
                "hold_until": hold.hold_until.isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error submitting deposit: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit deposit")


# ==================== STATUS TRACKING ====================

@router.get("/{deposit_id}/status")
async def get_deposit_status(
    deposit_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get current status of a mobile deposit"""
    try:
        result = await DepositStatusService.get_deposit_status(
            db=db,
            deposit_id=deposit_id
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting deposit status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


@router.get("/account/{account_id}/holds")
async def get_deposit_holds(
    account_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get all active deposit holds for an account"""
    try:
        result = await DepositStatusService.get_hold_information(
            db=db,
            account_id=account_id
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error getting holds: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve holds")


@router.get("/account/{account_id}/available-funds")
async def get_available_funds(
    account_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get available funds considering deposit holds"""
    try:
        result = await DepositStatusService.get_available_funds(
            db=db,
            account_id=account_id
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error getting available funds: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve available funds")


# ==================== DEPOSIT HISTORY ====================

@router.get("/account/{account_id}/deposits")
async def get_deposit_history(
    account_id: int = Query(..., gt=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get deposit history for an account"""
    try:
        deposits = db.query(MobileDeposit).filter(
            MobileDeposit.account_id == account_id
        ).order_by(MobileDeposit.created_at.desc()).limit(limit).all()
        
        return {
            "success": True,
            "count": len(deposits),
            "deposits": [
                {
                    "deposit_id": d.id,
                    "check_amount": d.check_amount,
                    "check_number": d.check_number,
                    "status": d.status,
                    "created_at": d.created_at.isoformat(),
                    "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None
                }
                for d in deposits
            ]
        }
    except Exception as e:
        log.error(f"Error getting deposit history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# ==================== EXCEPTION HANDLING ====================

@router.get("/{deposit_id}/exceptions")
async def get_deposit_exceptions(
    deposit_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get any exceptions or issues with a deposit"""
    try:
        from models import DepositException
        
        exceptions = db.query(DepositException).filter(
            DepositException.deposit_id == deposit_id
        ).all()
        
        return {
            "success": True,
            "count": len(exceptions),
            "exceptions": [
                {
                    "exception_id": e.id,
                    "type": e.exception_type,
                    "description": e.description,
                    "status": e.status,
                    "created_at": e.created_at.isoformat()
                }
                for e in exceptions
            ]
        }
    except Exception as e:
        log.error(f"Error getting exceptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exceptions")


# ==================== BATCH PROCESSING ====================

@router.post("/process-batch")
async def process_deposits_batch(
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Process all submitted deposits (scheduled job endpoint)
    Should be called periodically by job scheduler
    """
    try:
        # Get all submitted deposits
        submitted_deposits = db.query(MobileDeposit).filter(
            MobileDeposit.status == "submitted"
        ).all()
        
        processed_count = 0
        failed_count = 0
        
        for deposit in submitted_deposits:
            try:
                # Run quality checks and processing
                quality_result = await QualityCheckService.check_image_quality(
                    db=db,
                    deposit_id=deposit.id
                )
                
                if not quality_result["acceptable"]:
                    failed_count += 1
                    continue
                
                # Perform fraud detection
                fraud_result = await CheckProcessingService.detect_fraud(
                    db=db,
                    deposit_id=deposit.id
                )
                
                if fraud_result["risk_level"] == "high":
                    failed_count += 1
                    continue
                
                processed_count += 1
            except Exception as e:
                log.error(f"Error processing deposit {deposit.id}: {e}")
                failed_count += 1
        
        # Log to audit
        await AuditService.log_action(
            db=db,
            action="BATCH_DEPOSIT_PROCESSING",
            entity_type="MobileDeposit",
            entity_id=None,
            actor_id=current_user_id,
            details=f"Processed {processed_count} deposits, {failed_count} issues"
        )
        
        return {
            "success": True,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total": processed_count + failed_count
        }
    except Exception as e:
        log.error(f"Error processing batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch")
