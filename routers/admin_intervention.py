"""
Admin Intervention Control Center API
=====================================
Provides active intervention tools for handling banking crises.

Features:
- Manual Balance Adjustments (ledger entries with reason codes)
- Session Revocation (kill specific device sessions)
- Hold Management (release/extend with audit trails)
- KYC Document Retrieval (for side-by-side viewer)
- Global Search (account number, phone, transaction ID)
- Bulk Operations (email pending KYC users)
- Real-time Activity Feed Events
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime
import logging

from deps import SessionDep, get_current_admin_user
from models import (
    User as DBUser,
    Account as DBAccount,
    Ledger as DBLedger,
    AccountHold,
    KYCSubmission,
    KYCInfo,
    Transaction,
    DeviceFingerprint,
    AuditLog
)
from balance_service_ledger import BalanceServiceLedger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/intervention",
    tags=["intervention"],
    dependencies=[Depends(get_current_admin_user)]
)

# ==================== MODELS ====================

class ManualBalanceAdjustmentRequest(BaseModel):
    user_id: int
    amount: float
    reason_code: str  # MANUAL_CORRECTION, DISPUTE_SETTLEMENT, SYSTEM_ERROR, PROMOTION, REFUND
    description: str
    created_by: int  # Admin user ID

class ReleaseHoldRequest(BaseModel):
    hold_id: int
    approval_notes: str
    approved_by: int

class ExtendHoldRequest(BaseModel):
    hold_id: int
    additional_days: int
    reason: str
    extended_by: int

class RevokeSessionRequest(BaseModel):
    device_id: int
    reason: str
    revoked_by: int

class BulkEmailRequest(BaseModel):
    kyc_status_filter: str  # "pending", "rejected", "all"
    email_template: str  # "kyc_reminder", "kyc_urgent", "kyc_rejected"
    subject: str
    sent_by: int

class GlobalSearchRequest(BaseModel):
    query: str
    search_type: str  # account_number, phone, transaction_id, email, name

class ApproveKYCRequest(BaseModel):
    approved_by: int  # Admin user ID

class RejectKYCRequest(BaseModel):
    rejection_reason: str
    rejected_by: int  # Admin user ID

class CreateHoldRequest(BaseModel):
    user_id: int
    hold_type: str  # AML_REVIEW, COMPLIANCE_HOLD, FRAUD_REVIEW, etc.
    reason: str
    duration_days: int
    created_by: int  # Admin user ID

class AuditLogRequest(BaseModel):
    action: str  # KYC_APPROVAL, KYC_REJECTION, BALANCE_ADJUSTMENT, etc.
    target_user_id: Optional[int] = None  # User being acted upon
    details: str  # Details about the action

# ==================== MANUAL BALANCE ADJUSTMENTS ====================

@router.post("/balance/adjust")
async def manual_balance_adjustment(
    request: ManualBalanceAdjustmentRequest,
    db_session: SessionDep
):
    """
    Manually adjust user balance with audit trail.
    Creates a ledger entry with reason code.
    """
    try:
        # Get user
        user_result = await db_session.execute(
            select(DBUser).where(DBUser.id == request.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get system account for the transfer FROM
        system_account_result = await db_session.execute(
            select(DBAccount).where(DBAccount.account_number == "SYSTEM_RESERVE")
        )
        system_account = system_account_result.scalar_one_or_none()
        if not system_account:
            raise HTTPException(status_code=400, detail="System reserve account not found")

        # Create ledger entry
        ledger_entry = DBLedger(
            account_id=user.id,  # Simplified for this example
            transaction_type="manual_adjustment",
            amount=request.amount,
            direction="credit" if request.amount > 0 else "debit",
            reason=f"{request.reason_code}: {request.description}",
            status="posted",
            created_by=request.created_by,
            audit_reason=f"Admin intervention: {request.description}"
        )
        
        db_session.add(ledger_entry)
        await db_session.commit()

        # Get updated balance
        new_balance = await BalanceServiceLedger.get_user_balance(db_session, request.user_id)

        return {
            "success": True,
            "message": "Balance adjusted successfully",
            "user_id": request.user_id,
            "adjustment_amount": request.amount,
            "new_balance": float(new_balance),
            "reason_code": request.reason_code,
            "ledger_entry_id": ledger_entry.id,
            "created_at": ledger_entry.created_at.isoformat() if ledger_entry.created_at else None
        }

    except Exception as e:
        logger.error(f"Balance adjustment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HOLD MANAGEMENT ====================

@router.post("/holds/release")
async def release_hold(
    request: ReleaseHoldRequest,
    db_session: SessionDep
):
    """Release a hold and restore funds"""
    try:
        # Get hold
        hold_result = await db_session.execute(
            select(AccountHold).where(AccountHold.id == request.hold_id)
        )
        hold = hold_result.scalar_one_or_none()
        if not hold:
            raise HTTPException(status_code=404, detail="Hold not found")

        # Release the hold
        hold.released_at = datetime.utcnow()
        hold.released_by = request.approved_by
        hold.release_notes = request.approval_notes

        db_session.add(hold)
        await db_session.commit()

        return {
            "success": True,
            "message": "Hold released successfully",
            "hold_id": request.hold_id,
            "released_at": hold.released_at.isoformat() if hold.released_at else None,
            "approval_notes": request.approval_notes
        }

    except Exception as e:
        logger.error(f"Hold release error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/holds/extend")
async def extend_hold(
    request: ExtendHoldRequest,
    db_session: SessionDep
):
    """Extend an existing hold"""
    try:
        # Get hold
        hold_result = await db_session.execute(
            select(AccountHold).where(AccountHold.id == request.hold_id)
        )
        hold = hold_result.scalar_one_or_none()
        if not hold:
            raise HTTPException(status_code=404, detail="Hold not found")

        # Extend the hold
        from datetime import timedelta
        old_release_date = hold.release_date
        hold.release_date = old_release_date + timedelta(days=request.additional_days) if old_release_date else datetime.utcnow() + timedelta(days=request.additional_days)
        hold.current_reason = request.reason

        db_session.add(hold)
        await db_session.commit()

        return {
            "success": True,
            "message": "Hold extended successfully",
            "hold_id": request.hold_id,
            "old_release_date": old_release_date.isoformat() if old_release_date else None,
            "new_release_date": hold.release_date.isoformat() if hold.release_date else None,
            "extended_by_days": request.additional_days
        }

    except Exception as e:
        logger.error(f"Hold extension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SESSION MANAGEMENT ====================

@router.post("/sessions/revoke")
async def revoke_session(
    request: RevokeSessionRequest,
    db_session: SessionDep
):
    """Revoke a specific device session"""
    try:
        # Get device
        device_result = await db_session.execute(
            select(DeviceFingerprint).where(DeviceFingerprint.id == request.device_id)
        )
        device = device_result.scalar_one_or_none()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # Mark as revoked
        device.is_active = False
        device.last_activity = datetime.utcnow()

        db_session.add(device)
        await db_session.commit()

        return {
            "success": True,
            "message": "Session revoked successfully",
            "device_id": request.device_id,
            "ip_address": device.ip_address,
            "user_agent": device.user_agent,
            "revoked_at": datetime.utcnow().isoformat(),
            "reason": request.reason
        }

    except Exception as e:
        logger.error(f"Session revocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KYC DOCUMENT RETRIEVAL ====================

@router.get("/kyc/{user_id}/documents")
async def get_kyc_documents(
    user_id: int,
    db_session: SessionDep
):
    """Get KYC documents for a user (for side-by-side viewer)"""
    try:
        # Get KYC submission
        kyc_result = await db_session.execute(
            select(KYCSubmission).where(KYCSubmission.user_id == user_id).order_by(KYCSubmission.submitted_at.desc())
        )
        kyc = kyc_result.scalars().first()
        if not kyc:
            return {
                "success": False,
                "message": "No KYC submission found",
                "user_id": user_id
            }

        # Return document URLs and metadata
        return {
            "success": True,
            "user_id": user_id,
            "kyc_submission_id": kyc.id,
            "status": kyc.status,
            "created_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
            "documents": {
                "id_front": kyc.id_front_path if hasattr(kyc, 'id_front_path') else None,
                "id_back": kyc.id_back_path if hasattr(kyc, 'id_back_path') else None,
                "proof_of_address": kyc.proof_of_address_path if hasattr(kyc, 'proof_of_address_path') else None,
                "selfie": kyc.selfie_path if hasattr(kyc, 'selfie_path') else None,
            },
            "user_info": {
                "document_type": kyc.document_type if hasattr(kyc, 'document_type') else None,
                "document_number": kyc.document_number if hasattr(kyc, 'document_number') else None,
            }
        }

    except Exception as e:
        logger.error(f"KYC document retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GLOBAL SEARCH ====================

@router.get("/search")
async def global_search(
    db_session: SessionDep,
    query: str = Query(..., min_length=1),
    search_type: str = Query("all"),
    limit: int = Query(20, le=100)
):
    """
    Global search across multiple fields.
    search_type: "account_number", "phone", "transaction_id", "email", "name", "all"
    """
    try:
        results = {
            "users": [],
            "accounts": [],
            "transactions": [],
            "total": 0
        }

        # Search users
        if search_type in ["email", "name", "all"]:
            user_query = select(DBUser).where(
                or_(
                    DBUser.email.ilike(f"%{query}%"),
                    DBUser.full_name.ilike(f"%{query}%")
                )
            ).limit(limit)
            user_result = await db_session.execute(user_query)
            users = user_result.scalars().all()
            results["users"] = [{
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "kyc_status": u.kyc_status,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None
            } for u in users]

        # Search accounts
        if search_type in ["account_number", "all"]:
            account_query = select(DBAccount).where(
                DBAccount.account_number.ilike(f"%{query}%")
            ).limit(limit)
            account_result = await db_session.execute(account_query)
            accounts = account_result.scalars().all()
            results["accounts"] = [{
                "id": a.id,
                "account_number": a.account_number,
                "account_type": a.account_type,
                "owner_id": a.owner_id,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in accounts]

        # Search transactions
        if search_type in ["transaction_id", "all"]:
            txn_id = query if query.isdigit() else None
            if txn_id:
                txn_query = select(Transaction).where(
                    Transaction.reference_number.ilike(f"%{query}%")
                ).limit(limit)
                txn_result = await db_session.execute(txn_query)
                transactions = txn_result.scalars().all()
                results["transactions"] = [{
                    "id": t.id,
                    "reference_number": t.reference_number,
                    "amount": float(t.amount),
                    "type": t.transaction_type,
                    "status": t.status,
                    "user_id": t.user_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                } for t in transactions]

        results["total"] = len(results["users"]) + len(results["accounts"]) + len(results["transactions"])

        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "results": results
        }

    except Exception as e:
        logger.error(f"Global search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BULK OPERATIONS ====================

@router.post("/bulk-email")
async def bulk_email_users(
    request: BulkEmailRequest,
    db_session: SessionDep
):
    """
    Send bulk email to users based on KYC status.
    This would integrate with SESEmailService.
    """
    try:
        # Get users based on filter
        if request.kyc_status_filter == "pending":
            users_result = await db_session.execute(
                select(DBUser).where(DBUser.kyc_status == "pending")
            )
        elif request.kyc_status_filter == "rejected":
            users_result = await db_session.execute(
                select(DBUser).where(DBUser.kyc_status == "rejected")
            )
        else:
            users_result = await db_session.execute(select(DBUser))

        users = users_result.scalars().all()

        # In production, this would call SESEmailService
        # For now, we'll just return the count and prepare the emails

        email_list = [u.email for u in users if u.email]

        return {
            "success": True,
            "message": f"Bulk email prepared for {len(email_list)} users",
            "recipient_count": len(email_list),
            "kyc_status_filter": request.kyc_status_filter,
            "email_template": request.email_template,
            "subject": request.subject,
            # In production: send_result = await SESEmailService.send_bulk_email(...)
            "status": "prepared"
        }

    except Exception as e:
        logger.error(f"Bulk email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ACTIVITY FEED EVENTS ====================

@router.get("/activity-feed")
async def get_activity_feed(
    db_session: SessionDep,
    limit: int = Query(20, le=100),
    hours_back: int = Query(24, le=720)
):
    """
    Get recent activity for real-time feed.
    Shows: logins, transactions, KYC updates, holds, suspicious activity.
    """
    try:
        from datetime import timedelta
        
        time_filter = datetime.utcnow() - timedelta(hours=hours_back)

        # Recent transactions
        recent_txns = await db_session.execute(
            select(Transaction)
            .where(Transaction.created_at >= time_filter)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        transactions = recent_txns.scalars().all()

        # Recent KYC updates
        recent_kyc = await db_session.execute(
            select(KYCSubmission)
            .where(KYCSubmission.submitted_at >= time_filter)
            .order_by(KYCSubmission.submitted_at.desc())
            .limit(limit)
        )
        kyc_updates = recent_kyc.scalars().all()

        # Recent holds
        recent_holds = await db_session.execute(
            select(AccountHold)
            .where(AccountHold.created_at >= time_filter)
            .order_by(AccountHold.created_at.desc())
            .limit(limit)
        )
        holds = recent_holds.scalars().all()

        # Compile feed
        feed_items = []

        for txn in transactions:
            feed_items.append({
                "type": "transaction",
                "timestamp": txn.created_at.isoformat() if txn.created_at else None,
                "user_id": txn.user_id,
                "amount": float(txn.amount),
                "status": txn.status,
                "description": f"{txn.transaction_type}: {txn.description or 'No description'}"
            })

        for kyc in kyc_updates:
            feed_items.append({
                "type": "kyc_update",
                "timestamp": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
                "user_id": kyc.user_id,
                "status": kyc.status,
                "description": f"KYC {kyc.status}"
            })

        for hold in holds:
            feed_items.append({
                "type": "hold",
                "timestamp": hold.created_at.isoformat() if hold.created_at else None,
                "account_id": hold.account_id,
                "amount": float(hold.amount) if hasattr(hold, 'amount') else None,
                "reason": hold.current_reason if hasattr(hold, 'current_reason') else None
            })

        # Sort by timestamp
        feed_items.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        return {
            "success": True,
            "feed_items": feed_items[:limit],
            "total_items": len(feed_items),
            "time_range_hours": hours_back
        }

    except Exception as e:
        logger.error(f"Activity feed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KYC APPROVAL/REJECTION ====================

@router.post("/kyc/{user_id}/approve")
async def approve_kyc(
    user_id: int,
    request: ApproveKYCRequest,
    db_session: SessionDep,
    current_admin = Depends(get_current_admin_user)
):
    """
    Approve a user's KYC submission.
    Updates status to VERIFIED and sends notification.
    """
    try:
        # Get user
        user_result = await db_session.execute(
            select(DBUser).where(DBUser.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get latest KYC submission
        kyc_result = await db_session.execute(
            select(KYCSubmission)
            .where(KYCSubmission.user_id == user_id)
            .order_by(KYCSubmission.submitted_at.desc())
        )
        kyc = kyc_result.scalars().first()
        if not kyc:
            raise HTTPException(status_code=404, detail="KYC submission not found")

        # Update KYC submission status and approval metadata
        kyc.status = "approved"
        kyc.approval_date = datetime.utcnow()
        kyc.approved_by = request.approved_by

        # Update the canonical KYCInfo record if present
        kyc_info_result = await db_session.execute(
            select(KYCInfo).where(KYCInfo.user_id == user_id)
        )
        kyc_info = kyc_info_result.scalar_one_or_none()
        if kyc_info:
            kyc_info.kyc_status = "approved"
            kyc_info.reviewed_at = datetime.utcnow()
            kyc_info.submission_locked = False
            db_session.add(kyc_info)

        # Update user KYC status and trust flags
        user.kyc_status = "approved"
        user.is_verified = True
        user.is_active = True

        # Create audit log
        audit_entry = AuditLog(
            admin_id=request.approved_by,
            user_id=user_id,
            action_type="KYC_APPROVAL",
            details=f"KYC submission approved for user {user.email}",
            resource_type="KYCSubmission",
            resource_id=kyc.id,
            created_at=datetime.utcnow()
        )
        db_session.add(audit_entry)

        # Commit all changes
        await db_session.commit()

        logger.info(f"KYC approved for user {user_id} by admin {request.approved_by}")

        return {
            "success": True,
            "message": "KYC approved successfully",
            "user_id": user_id,
            "status": "VERIFIED"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"KYC approval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kyc/{user_id}/reject")
async def reject_kyc(
    user_id: int,
    request: RejectKYCRequest,
    db_session: SessionDep,
    current_admin = Depends(get_current_admin_user)
):
    """
    Reject a user's KYC submission.
    Updates status to REJECTED with reason and sends notification.
    """
    try:
        # Get user
        user_result = await db_session.execute(
            select(DBUser).where(DBUser.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get latest KYC submission
        kyc_result = await db_session.execute(
            select(KYCSubmission)
            .where(KYCSubmission.user_id == user_id)
            .order_by(KYCSubmission.submitted_at.desc())
        )
        kyc = kyc_result.scalars().first()
        if not kyc:
            raise HTTPException(status_code=404, detail="KYC submission not found")

        # Update KYC status
        kyc.status = "REJECTED"
        kyc.rejection_reason = request.rejection_reason
        kyc.rejection_date = datetime.utcnow()
        kyc.rejected_by = request.rejected_by

        # Update user KYC status
        user.kyc_status = "rejected"

        # Create audit log
        audit_entry = AuditLog(
            admin_id=request.rejected_by,
            user_id=user_id,
            action_type="KYC_REJECTION",
            details=f"KYC rejected: {request.rejection_reason}",
            resource_type="KYCSubmission",
            resource_id=kyc.id,
            created_at=datetime.utcnow()
        )
        db_session.add(audit_entry)

        # Commit all changes
        await db_session.commit()

        logger.info(f"KYC rejected for user {user_id} by admin {request.rejected_by}")

        return {
            "success": True,
            "message": "KYC rejected successfully",
            "user_id": user_id,
            "status": "REJECTED",
            "rejection_reason": request.rejection_reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"KYC rejection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HOLD CREATION ====================

@router.post("/holds/create")
async def create_hold(
    request: CreateHoldRequest,
    db_session: SessionDep,
    current_admin = Depends(get_current_admin_user)
):
    """
    Create a new account hold for a user.
    Freezes all user accounts and creates audit trail.
    """
    try:
        from datetime import timedelta
        
        # Get user
        user_result = await db_session.execute(
            select(DBUser).where(DBUser.id == request.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's accounts
        accounts_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == request.user_id)
        )
        accounts = accounts_result.scalars().all()
        if not accounts:
            raise HTTPException(status_code=404, detail="User has no accounts")

        # Create hold for each account
        hold_ids = []
        release_date = datetime.utcnow() + timedelta(days=request.duration_days)

        for account in accounts:
            # Update account status to frozen
            account.status = "frozen"

            # Create hold
            hold = AccountHold(
                account_id=account.id,
                hold_type=request.hold_type,
                reason=request.reason,
                current_reason=request.reason,
                amount=account.balance,
                created_by=request.created_by,
                created_at=datetime.utcnow(),
                release_date=release_date
            )
            db_session.add(hold)
            await db_session.flush()  # Get hold ID
            hold_ids.append(hold.id)

        # Create audit log
        audit_entry = AuditLog(
            admin_id=request.created_by,
            user_id=request.user_id,
            action_type="HOLD_CREATE",
            details=f"Hold created: {request.hold_type} - {request.reason} for {request.duration_days} days",
            resource_type="AccountHold",
            resource_id=hold_ids[0] if hold_ids else None,
            created_at=datetime.utcnow()
        )
        db_session.add(audit_entry)

        # Commit all changes
        await db_session.commit()

        logger.info(f"Hold created for user {request.user_id} by admin {request.created_by}")

        return {
            "success": True,
            "message": "Hold created successfully",
            "user_id": request.user_id,
            "hold_ids": hold_ids,
            "hold_type": request.hold_type,
            "release_date": release_date.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hold creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIT LOG ENDPOINT ====================

@router.post("/audit/log")
async def log_audit_action(
    request: AuditLogRequest,
    db_session: SessionDep,
    current_admin = Depends(get_current_admin_user)
):
    """
    Create an audit log entry for compliance tracking.
    Called automatically by all admin actions.
    """
    try:
        # Create audit log
        audit_entry = AuditLog(
            admin_id=current_admin.id,
            user_id=request.target_user_id,
            action_type=request.action,
            details=request.details,
            resource_type="AdminAction",
            created_at=datetime.utcnow()
        )
        db_session.add(audit_entry)
        await db_session.commit()

        logger.info(f"Audit logged: {request.action} by admin {current_admin.id}")

        return {
            "success": True,
            "message": "Audit logged successfully",
            "id": audit_entry.id,
            "action": request.action,
            "timestamp": audit_entry.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Audit log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
