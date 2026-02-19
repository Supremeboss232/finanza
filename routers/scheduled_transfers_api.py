"""API routes for scheduled transfers feature - Priority 3."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timedelta, time
from decimal import Decimal
import logging

from deps import get_db, get_current_user
from models_priority_3 import ScheduledTransfer, ScheduledTransferExecution
from models import User, Account, Transaction
from schemas_priority_3 import (
    ScheduledTransferCreate,
    ScheduledTransferUpdate,
    ScheduledTransferResponse,
    ScheduledTransferExecutionResponse,
)
from services_priority_3 import ScheduledTransfersService

router = APIRouter(prefix="/api/scheduled-transfers", tags=["scheduled-transfers"])
log = logging.getLogger(__name__)


# ==================== SCHEDULED TRANSFERS ENDPOINTS ====================

@router.post("/scheduled")
async def create_scheduled_transfer(
    account_id: int = Query(..., gt=0),
    amount: float = Query(..., gt=0),
    scheduled_date: datetime = Query(...),
    transfer_type: str = Query("ach"),
    description: Optional[str] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a one-time scheduled transfer
    
    - **transfer_type**: ach, wire, transfer_internal, push_payment
    - **scheduled_date**: ISO format datetime for when transfer should execute
    """
    try:
        # Verify account exists and belongs to user
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Create scheduled transfer
        result = await ScheduledTransferService.create_transfer(
            db=db,
            account_id=account_id,
            amount=amount,
            scheduled_date=scheduled_date,
            transfer_type=transfer_type,
            memo=description,
            created_by=current_user_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="TRANSFER_SCHEDULED",
                entity_type="ScheduledTransfer",
                entity_id=result["transfer_id"],
                actor_id=current_user_id,
                details=f"Scheduled ${amount} transfer"
            )
            return {
                "success": True,
                "transfer_id": result.get("transfer_id"),
                "status": "scheduled",
                "amount": amount,
                "scheduled_date": scheduled_date.isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error creating scheduled transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to create transfer")


@router.get("/scheduled")
async def list_scheduled_transfers(
    account_id: int = Query(..., gt=0),
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all scheduled transfers for an account"""
    try:
        result = await ScheduledTransferService.get_scheduled_transfers(
            db=db,
            account_id=account_id
        )
        
        if result["success"]:
            transfers = result["transfers"]
            
            # Filter by status if provided
            if status:
                transfers = [t for t in transfers if t["status"] == status]
            
            # Limit results
            transfers = transfers[:limit]
            
            return {
                "success": True,
                "count": len(transfers),
                "transfers": transfers
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error listing scheduled transfers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transfers")


@router.get("/scheduled/{transfer_id}")
async def get_scheduled_transfer_details(
    transfer_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get details of a specific scheduled transfer"""
    try:
        transfer = db.query(ScheduledTransfer).filter(
            ScheduledTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        return {
            "success": True,
            "transfer": {
                "transfer_id": transfer.id,
                "account_id": transfer.account_id,
                "amount": transfer.amount,
                "scheduled_date": transfer.scheduled_date.isoformat(),
                "status": transfer.status,
                "transfer_type": transfer.transfer_type,
                "description": transfer.description,
                "created_at": transfer.created_at.isoformat(),
                "executed_at": transfer.executed_at.isoformat() if transfer.executed_at else None,
                "failed_reason": transfer.failed_reason
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve transfer")


@router.put("/scheduled/{transfer_id}")
async def update_scheduled_transfer(
    transfer_id: int,
    amount: Optional[float] = Query(None, gt=0),
    scheduled_date: Optional[datetime] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Update a scheduled transfer (before execution)
    Can only update pending/scheduled transfers
    """
    try:
        transfer = db.query(ScheduledTransfer).filter(
            ScheduledTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        
        if transfer.status not in ["scheduled", "pending"]:
            raise HTTPException(status_code=400, detail=f"Cannot update {transfer.status} transfer")
        
        if amount:
            transfer.amount = amount
        if scheduled_date:
            transfer.scheduled_date = scheduled_date
        
        db.commit()
        
        # Log to audit
        await AuditService.log_action(
            db=db,
            action="TRANSFER_UPDATED",
            entity_type="ScheduledTransfer",
            entity_id=transfer_id,
            actor_id=current_user_id,
            details="Updated scheduled transfer"
        )
        
        return {
            "success": True,
            "transfer_id": transfer_id,
            "updated_fields": ["amount"] if amount else [] + ["scheduled_date"] if scheduled_date else []
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error updating transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to update transfer")


@router.delete("/scheduled/{transfer_id}")
async def cancel_scheduled_transfer(
    transfer_id: int,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Cancel a scheduled transfer"""
    try:
        result = await ScheduledTransferService.cancel_transfer(
            db=db,
            transfer_id=transfer_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="TRANSFER_CANCELLED",
                entity_type="ScheduledTransfer",
                entity_id=transfer_id,
                actor_id=current_user_id,
                details="Cancelled scheduled transfer"
            )
            return {"success": True, "transfer_id": transfer_id, "status": "cancelled"}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error cancelling transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel transfer")


# ==================== RECURRING TRANSFERS ENDPOINTS ====================

@router.post("/recurring")
async def setup_recurring_transfer(
    account_id: int = Query(..., gt=0),
    amount: float = Query(..., gt=0),
    frequency: str = Query(...),  # daily, weekly, biweekly, monthly
    start_date: datetime = Query(...),
    end_date: Optional[datetime] = None,
    transfer_type: str = Query("ach"),
    description: Optional[str] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Setup a recurring transfer with automatic execution
    
    - **frequency**: daily, weekly, biweekly, monthly
    """
    try:
        # Verify account
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        result = await RecurringTransferService.setup_recurring(
            db=db,
            account_id=account_id,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            transfer_type=transfer_type,
            memo=description,
            created_by=current_user_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="RECURRING_TRANSFER_SETUP",
                entity_type="RecurringTransfer",
                entity_id=result.get("recurring_id"),
                actor_id=current_user_id,
                details=f"Setup {frequency} recurring transfer of ${amount}"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error setting up recurring transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup recurring transfer")


@router.get("/recurring")
async def list_recurring_transfers(
    account_id: int = Query(..., gt=0),
    status: Optional[str] = Query("active"),
    db: Session = Depends(get_db)
):
    """Get all recurring transfers for an account"""
    try:
        query = db.query(RecurringTransfer).filter(
            RecurringTransfer.account_id == account_id
        )
        
        if status:
            query = query.filter(RecurringTransfer.status == status)
        
        transfers = query.all()
        
        return {
            "success": True,
            "count": len(transfers),
            "recurring_transfers": [
                {
                    "recurring_id": t.id,
                    "amount": t.amount,
                    "frequency": t.frequency,
                    "status": t.status,
                    "start_date": t.start_date.isoformat(),
                    "end_date": t.end_date.isoformat() if t.end_date else None,
                    "created_at": t.created_at.isoformat()
                }
                for t in transfers
            ]
        }
    except Exception as e:
        log.error(f"Error listing recurring transfers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recurring transfers")


@router.put("/recurring/{recurring_id}")
async def modify_recurring_transfer(
    recurring_id: int,
    amount: Optional[float] = Query(None, gt=0),
    frequency: Optional[str] = None,
    end_date: Optional[datetime] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Modify an active recurring transfer"""
    try:
        result = await RecurringTransferService.modify_recurring(
            db=db,
            recurring_id=recurring_id,
            amount=amount,
            frequency=frequency,
            end_date=end_date
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="RECURRING_TRANSFER_MODIFIED",
                entity_type="RecurringTransfer",
                entity_id=recurring_id,
                actor_id=current_user_id,
                details="Modified recurring transfer"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error modifying recurring transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to modify recurring transfer")


@router.post("/recurring/{recurring_id}/suspend")
async def suspend_recurring_transfer(
    recurring_id: int,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Temporarily suspend a recurring transfer"""
    try:
        result = await RecurringTransferService.suspend_recurring(
            db=db,
            recurring_id=recurring_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="RECURRING_TRANSFER_SUSPENDED",
                entity_type="RecurringTransfer",
                entity_id=recurring_id,
                actor_id=current_user_id,
                details="Suspended recurring transfer"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error suspending recurring transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to suspend recurring transfer")


@router.post("/recurring/{recurring_id}/resume")
async def resume_recurring_transfer(
    recurring_id: int,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Resume a suspended recurring transfer"""
    try:
        result = await RecurringTransferService.resume_recurring(
            db=db,
            recurring_id=recurring_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="RECURRING_TRANSFER_RESUMED",
                entity_type="RecurringTransfer",
                entity_id=recurring_id,
                actor_id=current_user_id,
                details="Resumed recurring transfer"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error resuming recurring transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume recurring transfer")


# ==================== EXECUTION HISTORY ENDPOINTS ====================

@router.get("/executions")
async def get_execution_history(
    account_id: int = Query(..., gt=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get transfer execution history for account"""
    try:
        from models import TransferExecution
        
        executions = db.query(TransferExecution).filter(
            TransferExecution.account_id == account_id
        ).order_by(TransferExecution.executed_date.desc()).limit(limit).all()
        
        return {
            "success": True,
            "count": len(executions),
            "executions": [
                {
                    "execution_id": e.id,
                    "amount": e.amount,
                    "status": e.status,
                    "executed_date": e.executed_date.isoformat(),
                    "failure_reason": e.failure_reason,
                    "transaction_id": e.transaction_id
                }
                for e in executions
            ]
        }
    except Exception as e:
        log.error(f"Error retrieving execution history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


# ==================== BATCH PROCESSING ENDPOINT ====================

@router.post("/process-scheduled")
async def process_scheduled_transfers_batch(
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Process all due scheduled transfers (scheduled job endpoint)
    Should be called periodically (e.g., hourly) by job scheduler
    """
    try:
        result = await TransferScheduleService.process_batch_transfers(db=db)
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="BATCH_TRANSFER_PROCESSING",
                entity_type="TransferSchedule",
                entity_id=None,
                actor_id=current_user_id,
                details=f"Processed {result.get('processed_count', 0)} transfers"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error processing batch transfers: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch")
"""API routes for scheduled transfers feature - Priority 3."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timedelta, time
from decimal import Decimal
import logging

from deps import get_db, get_current_user
from models_priority_3 import ScheduledTransfer, ScheduledTransferExecution
from models import User, Account
from schemas_priority_3 import (
    ScheduledTransferCreate,
    ScheduledTransferUpdate,
    ScheduledTransferResponse,
    ScheduledTransferExecutionResponse,
)
from services_priority_3 import ScheduledTransfersService

router = APIRouter(prefix="/api/v1/scheduled-transfers", tags=["scheduled-transfers"])
log = logging.getLogger(__name__)


# ============================================================================
# SCHEDULED TRANSFER ENDPOINTS (5 ENDPOINTS)
# ============================================================================

@router.post("/create", response_model=ScheduledTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_transfer(
    request: ScheduledTransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new scheduled transfer.
    
    - **from_account_id**: Source account ID
    - **to_account_id**: Destination account ID
    - **amount**: Transfer amount
    - **frequency**: once, daily, weekly, monthly, yearly
    - **start_date**: When to start executing transfers
    - **end_date**: Optional end date for recurring transfers
    - **start_time**: Time of day to execute (HH:MM format)
    """
    
    # Validate user owns both accounts
    from_account = db.query(Account).filter(
        Account.id == request.from_account_id,
        Account.user_id == current_user.id
    ).first()
    
    to_account = db.query(Account).filter(
        Account.id == request.to_account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not from_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source account not found"
        )
    
    if not to_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination account not found"
        )
    
    # Validate source account has sufficient balance
    if from_account.balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance in source account"
        )
    
    # Validate dates
    if request.end_date and request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    # Create scheduled transfer
    scheduled_transfer = ScheduledTransfer(
        user_id=current_user.id,
        from_account_id=request.from_account_id,
        to_account_id=request.to_account_id,
        amount=request.amount,
        frequency=request.frequency,
        start_date=request.start_date,
        end_date=request.end_date,
        start_time=request.start_time,
        status="active",
        description=request.description,
    )
    
    db.add(scheduled_transfer)
    db.commit()
    db.refresh(scheduled_transfer)
    
    log.info(f"Created scheduled transfer {scheduled_transfer.id} for user {current_user.id}")
    
    return scheduled_transfer


@router.get("/list", response_model=List[ScheduledTransferResponse])
async def list_scheduled_transfers(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    frequency: Optional[str] = Query(None, description="Filter by frequency"),
    limit: int = Query(50, ge=1, le=100, description="Results limit"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of scheduled transfers for current user.
    
    - **status_filter**: Filter by status (active, paused, cancelled, completed)
    - **frequency**: Filter by frequency (once, daily, weekly, monthly, yearly)
    - **limit**: Maximum results (1-100)
    - **offset**: Pagination offset
    """
    
    query = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(ScheduledTransfer.status == status_filter)
    
    if frequency:
        query = query.filter(ScheduledTransfer.frequency == frequency)
    
    transfers = query.order_by(ScheduledTransfer.created_at.desc()).limit(limit).offset(offset).all()
    
    log.info(f"Retrieved {len(transfers)} scheduled transfers for user {current_user.id}")
    
    return transfers


@router.get("/{transfer_id}", response_model=ScheduledTransferResponse)
async def get_scheduled_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a scheduled transfer."""
    
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    return transfer


@router.put("/{transfer_id}", response_model=ScheduledTransferResponse)
async def update_scheduled_transfer(
    transfer_id: int,
    request: ScheduledTransferUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a scheduled transfer.
    
    Only allows updates to: amount, end_date, start_time, description
    Cannot update: frequency, accounts, user
    """
    
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    # Only allow updates if not completed
    if transfer.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update completed transfer"
        )
    
    # Update fields
    if request.amount is not None:
        transfer.amount = request.amount
    if request.end_date is not None:
        transfer.end_date = request.end_date
    if request.start_time is not None:
        transfer.start_time = request.start_time
    if request.description is not None:
        transfer.description = request.description
    
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(transfer)
    
    log.info(f"Updated scheduled transfer {transfer_id} for user {current_user.id}")
    
    return transfer


@router.post("/{transfer_id}/pause", response_model=ScheduledTransferResponse)
async def pause_scheduled_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pause a scheduled transfer."""
    
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    if transfer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only pause active transfers"
        )
    
    transfer.status = "paused"
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(transfer)
    
    log.info(f"Paused scheduled transfer {transfer_id}")
    
    return transfer


@router.post("/{transfer_id}/resume", response_model=ScheduledTransferResponse)
async def resume_scheduled_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resume a paused scheduled transfer."""
    
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    if transfer.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resume paused transfers"
        )
    
    transfer.status = "active"
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(transfer)
    
    log.info(f"Resumed scheduled transfer {transfer_id}")
    
    return transfer


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_scheduled_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a scheduled transfer."""
    
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    if transfer.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or already cancelled transfer"
        )
    
    transfer.status = "cancelled"
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    
    log.info(f"Cancelled scheduled transfer {transfer_id}")
    
    return None


# ============================================================================
# EXECUTION HISTORY ENDPOINTS
# ============================================================================

@router.get("/{transfer_id}/executions", response_model=List[ScheduledTransferExecutionResponse])
async def get_transfer_executions(
    transfer_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get execution history for a scheduled transfer."""
    
    # Verify ownership
    transfer = db.query(ScheduledTransfer).filter(
        ScheduledTransfer.id == transfer_id,
        ScheduledTransfer.user_id == current_user.id
    ).first()
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled transfer not found"
        )
    
    query = db.query(ScheduledTransferExecution).filter(
        ScheduledTransferExecution.scheduled_transfer_id == transfer_id
    )
    
    if status_filter:
        query = query.filter(ScheduledTransferExecution.status == status_filter)
    
    executions = query.order_by(
        ScheduledTransferExecution.execution_date.desc()
    ).limit(limit).offset(offset).all()
    
    return executions


@router.get("/executions/statistics", response_model=dict)
async def get_execution_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get execution statistics for user's scheduled transfers."""
    
    # Get all user's transfers
    transfers = db.query(ScheduledTransfer.id).filter(
        ScheduledTransfer.user_id == current_user.id
    ).all()
    
    transfer_ids = [t[0] for t in transfers]
    
    if not transfer_ids:
        return {
            "total_scheduled": 0,
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "pending": 0,
            "success_rate": 0.0,
            "total_amount_transferred": 0,
        }
    
    # Get statistics
    total_executions = db.query(func.count(ScheduledTransferExecution.id)).filter(
        ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids)
    ).scalar()
    
    successful = db.query(func.count(ScheduledTransferExecution.id)).filter(
        ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids),
        ScheduledTransferExecution.status == "completed"
    ).scalar()
    
    failed = db.query(func.count(ScheduledTransferExecution.id)).filter(
        ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids),
        ScheduledTransferExecution.status == "failed"
    ).scalar()
    
    pending = db.query(func.count(ScheduledTransferExecution.id)).filter(
        ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids),
        ScheduledTransferExecution.status == "pending"
    ).scalar()
    
    # Calculate success rate
    success_rate = (successful / total_executions * 100) if total_executions > 0 else 0
    
    # Get total amount transferred (from completed executions)
    total_amount = db.query(func.sum(ScheduledTransfer.amount)).filter(
        ScheduledTransfer.id.in_(transfer_ids),
        ScheduledTransfer.status.in_(["active", "paused", "completed"])
    ).scalar() or 0
    
    return {
        "total_scheduled": len(transfer_ids),
        "total_executions": total_executions or 0,
        "successful": successful or 0,
        "failed": failed or 0,
        "pending": pending or 0,
        "success_rate": float(success_rate),
        "total_amount_scheduled": float(total_amount),
    }
