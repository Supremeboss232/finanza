"""
Admin Management Endpoints
Provides admin access to user management data: holds, frozen accounts, credit scores, device fingerprinting
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from typing import List, Optional
from datetime import datetime
from deps import get_db, get_current_admin_user
from models import (
    User, Account, AccountHold, CreditScore, DeviceFingerprint, FraudScore
)
import logging

log = logging.getLogger(__name__)
router = APIRouter()

# ==================== ACCOUNT HOLDS ====================
@router.get("/api/admin/holds")
async def admin_get_holds(
    limit: int = Query(50, ge=1, le=100),
    skip: int = 0,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all account holds with optional user filter"""
    query = select(AccountHold)
    
    if user_id:
        # Get user's account IDs first
        accounts = await db.execute(select(Account.id).filter(Account.owner_id == user_id))
        account_ids = [acc[0] for acc in accounts.fetchall()]
        if not account_ids:
            return {"success": True, "data": [], "total": 0}
        query = query.filter(AccountHold.account_id.in_(account_ids))
    
    # Get total count
    count_query = select(User).select_from(AccountHold).join(
        Account, Account.id == AccountHold.account_id
    ).join(User, User.id == Account.owner_id)
    if user_id:
        count_query = count_query.filter(User.id == user_id)
    
    total_result = await db.execute(select(AccountHold))
    total = len(total_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        query.order_by(desc(AccountHold.created_at)).limit(limit).offset(skip)
    )
    holds = result.scalars().all()
    
    data = []
    for hold in holds:
        account = await db.get(Account, hold.account_id)
        user = await db.get(User, account.owner_id) if account else None
        
        data.append({
            "id": hold.id,
            "hold_id": hold.id,
            "user_id": user.id if user else None,
            "user_email": user.email if user else "Unknown",
            "email": user.email if user else "Unknown",
            "account_number": account.account_number if account else "Unknown",
            "hold_type": hold.reason,
            "reason": hold.reason,
            "hold_amount": None,
            "amount": None,
            "created_at": hold.created_at.isoformat() if hold.created_at else None,
            "released_at": hold.released_at.isoformat() if hold.released_at else None,
            "is_active": not bool(hold.released_at),
            "status": "active" if not hold.released_at else "released"
        })
    
    return {"success": True, "data": data, "total": total, "limit": limit, "skip": skip}

@router.get("/api/admin/holds/user/{user_id}")
async def admin_get_user_holds(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all holds for a specific user"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's accounts
    accounts_result = await db.execute(
        select(Account.id).filter(Account.owner_id == user_id)
    )
    account_ids = [acc[0] for acc in accounts_result.fetchall()]
    
    if not account_ids:
        return {"success": True, "data": [], "total": 0, "user_email": user.email}
    
    # Get holds
    result = await db.execute(
        select(AccountHold).filter(AccountHold.account_id.in_(account_ids))
        .order_by(desc(AccountHold.created_at))
    )
    holds = result.scalars().all()
    
    data = [
        {
            "hold_id": hold.id,
            "reason": hold.reason,
            "created_at": hold.created_at.isoformat() if hold.created_at else None,
            "released_at": hold.released_at.isoformat() if hold.released_at else None,
            "status": "active" if not hold.released_at else "released"
        }
        for hold in holds
    ]
    
    return {"success": True, "data": data, "total": len(data), "user_email": user.email}

# ==================== FROZEN ACCOUNTS ====================
@router.get("/api/admin/frozen-accounts")
async def admin_get_frozen_accounts(
    limit: int = Query(50, ge=1, le=100),
    skip: int = 0,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all frozen accounts"""
    # Query frozen accounts with join to user
    result = await db.execute(
        select(Account, User).join(User, User.id == Account.owner_id)
        .filter(Account.status == 'frozen')
        .order_by(desc(Account.updated_at))
        .limit(limit)
        .offset(skip)
    )
    
    accounts = result.all()
    
    # Get total
    total_result = await db.execute(
        select(Account).filter(Account.status == 'frozen')
    )
    total = len(total_result.scalars().all())
    
    data = []
    for account, user in accounts:
        data.append({
            "account_id": account.id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name or "N/A",
            "freeze_date": account.updated_at.isoformat() if account.updated_at else None,
            "reason": f"Account frozen - Status: {account.status}",
            "status": account.status,
            "account_number": account.account_number
        })
    
    return {"success": True, "data": data, "total": total, "limit": limit, "skip": skip}

@router.post("/api/admin/frozen-accounts/{account_id}/unfreeze")
async def admin_unfreeze_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Unfreeze an account"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.status != 'frozen':
        raise HTTPException(status_code=400, detail="Account is not frozen")
    
    account.status = 'active'
    account.updated_at = datetime.utcnow()
    db.add(account)
    await db.commit()
    
    log.info(f"Admin {current_admin.id} unfroze account {account_id}")
    
    return {
        "success": True,
        "message": f"Account {account.account_number} unfrozen",
        "account_id": account_id,
        "status": account.status
    }

# ==================== CREDIT SCORES ====================
@router.get("/api/admin/credit-scores")
async def admin_get_credit_scores(
    limit: int = Query(50, ge=1, le=100),
    skip: int = 0,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get recent credit scores"""
    query = select(CreditScore, User).join(User, User.id == CreditScore.user_id)
    
    if user_id:
        query = query.filter(CreditScore.user_id == user_id)
    
    # Get total
    count_result = await db.execute(
        select(CreditScore).filter(
            CreditScore.user_id == user_id if user_id else True
        )
    )
    total = len(count_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        query.order_by(desc(CreditScore.created_at))
        .limit(limit).offset(skip)
    )
    
    scores = result.all()
    
    data = []
    for score, user in scores:
        data.append({
            "score_id": score.id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name or "N/A",
            "current_score": score.score,
            "score_date": score.score_date.isoformat() if score.score_date else None,
            "created_at": score.created_at.isoformat() if score.created_at else None,
            "data_source": "Bureau" if score.score else "System"
        })
    
    return {"success": True, "data": data, "total": total, "limit": limit, "skip": skip}

@router.get("/api/admin/credit-scores/user/{user_id}")
async def admin_get_user_credit_scores(
    user_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get credit score history for a user"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.execute(
        select(CreditScore).filter(CreditScore.user_id == user_id)
        .order_by(desc(CreditScore.created_at))
        .limit(limit)
    )
    
    scores = result.scalars().all()
    
    data = []
    previous_score = None
    for score in scores:
        change = None
        if previous_score:
            change = score.score - previous_score
        
        data.append({
            "score": score.score,
            "score_date": score.score_date.isoformat() if score.score_date else None,
            "created_at": score.created_at.isoformat() if score.created_at else None,
            "previous_score": previous_score,
            "change": change,
            "data_source": "Bureau"
        })
        previous_score = score.score
    
    return {
        "success": True,
        "user_email": user.email,
        "data": data,
        "total": len(data)
    }

# ==================== DEVICE FINGERPRINTING ====================
@router.get("/api/admin/devices")
async def admin_get_devices(
    limit: int = Query(50, ge=1, le=100),
    skip: int = 0,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get registered devices with optional user filter"""
    query = select(DeviceFingerprint, User).join(User, User.id == DeviceFingerprint.user_id)
    
    if user_id:
        query = query.filter(DeviceFingerprint.user_id == user_id)
    
    # Get total
    total_result = await db.execute(
        select(DeviceFingerprint).filter(
            DeviceFingerprint.user_id == user_id if user_id else True
        )
    )
    total = len(total_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        query.order_by(desc(DeviceFingerprint.last_used))
        .limit(limit).offset(skip)
    )
    
    devices = result.all()
    
    data = []
    for device, user in devices:
        # Parse user agent for browser info
        user_agent = device.user_agent or ""
        browser = "Unknown"
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
        
        data.append({
            "device_id": device.id,
            "user_id": user.id,
            "email": user.email,
            "device_number": device.device_id,
            "device_type": "Mobile" if "Mobile" in user_agent else "Desktop",
            "ip_address": device.ip_address or "Unknown",
            "browser": browser,
            "first_seen": device.created_at.isoformat() if device.created_at else None,
            "last_active": device.last_used.isoformat() if device.last_used else None,
            "user_agent": user_agent[:100]  # Truncate for display
        })
    
    return {"success": True, "data": data, "total": total, "limit": limit, "skip": skip}

@router.get("/api/admin/devices/user/{user_id}")
async def admin_get_user_devices(
    user_id: int,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all registered devices for a specific user"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.execute(
        select(DeviceFingerprint).filter(DeviceFingerprint.user_id == user_id)
        .order_by(desc(DeviceFingerprint.last_used))
        .limit(limit)
    )
    
    devices = result.scalars().all()
    
    data = []
    for device in devices:
        user_agent = device.user_agent or ""
        browser = "Unknown"
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent:
            browser = "Safari"
        
        data.append({
            "device_id": device.id,
            "device_number": device.device_id,
            "device_type": "Mobile" if "Mobile" in user_agent else "Desktop",
            "ip_address": device.ip_address or "Unknown",
            "browser": browser,
            "first_seen": device.created_at.isoformat() if device.created_at else None,
            "last_active": device.last_used.isoformat() if device.last_used else None
        })
    
    return {
        "success": True,
        "user_email": user.email,
        "data": data,
        "total": len(data)
    }

# ==================== USER MANAGEMENT SUMMARY ====================
@router.get("/api/admin/users-summary")
async def admin_get_users_summary(
    limit: int = Query(50, ge=1, le=100),
    skip: int = 0,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get comprehensive user management summary with all data"""
    # Get users
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).limit(limit).offset(skip)
    )
    users = result.scalars().all()
    
    # Get total
    total_result = await db.execute(select(User))
    total = len(total_result.scalars().all())
    
    data = []
    for user in users:
        # Get user's account
        account_result = await db.execute(
            select(Account).filter(Account.owner_id == user.id).limit(1)
        )
        account = account_result.scalars().first()
        
        # Get holds count
        holds_result = await db.execute(
            select(AccountHold).filter(
                AccountHold.account_id == account.id if account else False
            )
        )
        holds_count = len(holds_result.scalars().all())
        
        # Get latest credit score
        score_result = await db.execute(
            select(CreditScore).filter(CreditScore.user_id == user.id)
            .order_by(desc(CreditScore.created_at)).limit(1)
        )
        latest_score = score_result.scalars().first()
        
        # Get devices count
        devices_result = await db.execute(
            select(DeviceFingerprint).filter(DeviceFingerprint.user_id == user.id)
        )
        devices_count = len(devices_result.scalars().all())
        
        data.append({
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name or "N/A",
            "status": account.status if account else "no_account",
            "kyc_status": user.kyc_status,
            "credit_score": latest_score.score if latest_score else None,
            "holds": holds_count,
            "is_frozen": account.status == "frozen" if account else False,
            "registered": user.created_at.isoformat() if user.created_at else None,
            "devices": devices_count
        })
    
    return {"success": True, "data": data, "total": total, "limit": limit, "skip": skip}
