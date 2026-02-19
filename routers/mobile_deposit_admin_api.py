"""Mobile Deposits Admin API - Priority 3."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from deps import get_db, get_current_user
from models_priority_3 import MobileDeposit
from models import User
from schemas_priority_3 import (
    MobileDepositCreate,
    MobileDepositUpdate,
    MobileDepositResponse,
)
from services_priority_3 import MobileDepositsService

router = APIRouter(prefix="/api/v1/mobile-deposits", tags=["mobile-deposits"])
log = logging.getLogger(__name__)


# ============================================================================
# USER ENDPOINTS (3 ENDPOINTS)
# ============================================================================

@router.post("/create", response_model=MobileDepositResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_deposit(
    request: MobileDepositCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new mobile deposit."""
    
    deposit = MobileDepositsService.create_deposit(
        db=db,
        user_id=current_user.id,
        account_id=request.account_id,
        amount=request.amount,
        front_image_url=request.front_image_url,
        back_image_url=request.back_image_url,
    )
    
    # Analyze images
    if request.front_image_url or request.back_image_url:
        analysis = MobileDepositsService.analyze_deposit_images(deposit)
        deposit.check_detected = analysis.get("check_detected")
        deposit.endorsement_found = analysis.get("endorsement_found")
        deposit.image_quality_score = analysis.get("image_quality_score")
        deposit.quality_score = analysis.get("quality_score")
    
    db.add(deposit)
    db.commit()
    db.refresh(deposit)
    
    log.info(f"Created mobile deposit {deposit.id} for user {current_user.id}")
    
    return deposit


@router.get("/list", response_model=List[MobileDepositResponse])
async def list_user_deposits(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's mobile deposits."""
    
    query = db.query(MobileDeposit).filter(
        MobileDeposit.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(MobileDeposit.status == status_filter)
    
    deposits = query.order_by(MobileDeposit.created_at.desc()).limit(limit).offset(offset).all()
    
    return deposits


# ============================================================================
# ADMIN ENDPOINTS (3 ENDPOINTS)
# ============================================================================

@router.get("/admin/list", response_model=List[MobileDepositResponse])
async def list_all_deposits(
    status_filter: Optional[str] = Query("pending", description="Filter by status"),
    sort_by: str = Query("quality_score", description="Sort field"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all mobile deposits (admin only). Defaults to showing pending deposits."""
    
    # Check admin
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    query = db.query(MobileDeposit)
    
    if status_filter:
        query = query.filter(MobileDeposit.status == status_filter)
    
    # Sort
    if sort_by == "quality_score":
        query = query.order_by(MobileDeposit.quality_score.asc() if status_filter == "pending" else MobileDeposit.created_at.desc())
    else:
        query = query.order_by(MobileDeposit.created_at.desc())
    
    deposits = query.limit(limit).offset(offset).all()
    
    return deposits


@router.post("/{deposit_id}/approve", response_model=MobileDepositResponse)
async def approve_deposit(
    deposit_id: int,
    request: MobileDepositUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a mobile deposit."""
    
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    deposit = db.query(MobileDeposit).get(deposit_id)
    
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deposit not found"
        )
    
    deposit = MobileDepositsService.approve_deposit(
        db=db,
        deposit=deposit,
        reviewer_id=current_user.id,
        review_notes=request.review_notes,
    )
    
    db.commit()
    db.refresh(deposit)
    
    log.info(f"Approved mobile deposit {deposit_id}")
    
    return deposit


@router.post("/{deposit_id}/reject", response_model=MobileDepositResponse)
async def reject_deposit(
    deposit_id: int,
    request: MobileDepositUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a mobile deposit."""
    
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    deposit = db.query(MobileDeposit).get(deposit_id)
    
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deposit not found"
        )
    
    if not request.review_notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason required"
        )
    
    deposit = MobileDepositsService.reject_deposit(
        db=db,
        deposit=deposit,
        reviewer_id=current_user.id,
        review_notes=request.review_notes,
    )
    
    db.commit()
    db.refresh(deposit)
    
    log.info(f"Rejected mobile deposit {deposit_id}")
    
    return deposit


@router.get("/admin/statistics")
async def get_deposit_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get mobile deposit statistics (admin only)."""
    
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    stats = MobileDepositsService.get_deposit_stats(db)
    
    return stats
