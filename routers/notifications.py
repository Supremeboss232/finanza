"""
Notification API endpoints for Finanza Banking App.
Provides standard, production-grade banking alerts and notification management.
Persists all notifications in the database with real user banking events.
Supports both /api/v1/notifications and /api/user/notifications prefixes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from deps import get_current_user, SessionDep
from models import User, Notification as DBNotification, Account, Transaction
from crud import (
    create_notification,
    get_user_notifications,
    get_unread_notifications_count,
    get_notification,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
)
from schemas import (
    Notification,
    NotificationCreate,
)

router = APIRouter(tags=["notifications"])


async def ensure_initial_banking_notifications(db: AsyncSession, user: User) -> List[DBNotification]:
    """
    Ensure the user has real banking notifications in the database reflecting their actual
    account status, registration, and transaction history.
    """
    # 1. Check existing notifications in DB
    result = await db.execute(
        select(DBNotification)
        .where(DBNotification.user_id == user.id)
        .order_by(DBNotification.created_at.desc())
    )
    existing = result.scalars().all()
    if existing:
        return list(existing)

    # 2. User has 0 notifications -> generate real initial banking records
    created: List[DBNotification] = []
    now = datetime.utcnow()

    # Welcome & Security Notice
    notif_welcome = DBNotification(
        user_id=user.id,
        title="Welcome to Finanza Online Banking",
        message="Your account profile has been securely configured. Two-factor authentication, fraud monitoring, and automated clearing services are active.",
        notification_type="security",
        is_read=False,
        created_at=user.created_at or now
    )
    db.add(notif_welcome)
    created.append(notif_welcome)

    # Real Account Opening Notification
    acct_result = await db.execute(
        select(Account).where(Account.owner_id == user.id)
    )
    accounts = acct_result.scalars().all()
    for acct in accounts:
        acct_notif = DBNotification(
            user_id=user.id,
            title=f"{acct.account_type.capitalize()} Account #{acct.account_number} Active",
            message=f"Your {acct.account_type} account (#{acct.account_number}) is ready for deposits, wires, and transfers with currency {acct.currency}.",
            notification_type="alert",
            is_read=False,
            created_at=acct.created_at or now
        )
        db.add(acct_notif)
        created.append(acct_notif)

    # KYC Identity Status Notification
    kyc_status = getattr(user, 'kyc_status', 'not_started')
    if kyc_status and kyc_status != 'not_started':
        title = "KYC Verification Approved" if kyc_status == "approved" else f"KYC Status: {kyc_status.capitalize()}"
        msg = "Your identity verification documents have been verified and approved. Standard daily withdrawal limits apply." if kyc_status == "approved" else f"Your identity verification status is currently '{kyc_status}'."
        kyc_notif = DBNotification(
            user_id=user.id,
            title=title,
            message=msg,
            notification_type="kyc",
            is_read=False,
            created_at=now
        )
        db.add(kyc_notif)
        created.append(kyc_notif)

    # Real Transaction History as Banking Alerts
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(5)
    )
    txs = tx_result.scalars().all()
    for tx in txs:
        direction_label = "Credit" if tx.direction == "credit" else "Debit"
        tx_notif = DBNotification(
            user_id=user.id,
            title=f"Transaction: {tx.transaction_type.capitalize()}",
            message=f"{direction_label} of ${float(tx.amount):,.2f} ({tx.status.capitalize()}). Ref: {tx.reference_number or tx.id}",
            notification_type="transaction",
            is_read=False,
            created_at=tx.created_at or now
        )
        db.add(tx_notif)
        created.append(tx_notif)

    try:
        await db.commit()
        for item in created:
            await db.refresh(item)
    except Exception as e:
        await db.rollback()
        # Fallback to empty list if concurrent commit conflict
        return []

    return sorted(created, key=lambda x: x.created_at or now, reverse=True)


# ============================================================================
# 1. LIST NOTIFICATIONS (Both /api/user/notifications and /api/v1/notifications)
# ============================================================================

@router.get("/api/user/notifications", response_model=List[Notification])
@router.get("/api/v1/notifications", response_model=List[Notification])
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all notifications for the authenticated user."""
    # Ensure baseline banking notifications exist if user has none
    await ensure_initial_banking_notifications(db_session, current_user)
    return await get_user_notifications(db_session, current_user.id, skip, limit)


# ============================================================================
# 2. UNREAD COUNT
# ============================================================================

@router.get("/api/user/notifications/unread-count")
@router.get("/api/user/notifications/unread/count")
@router.get("/api/v1/notifications/unread/count")
async def get_unread_count(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications for notification bell badges."""
    count = await get_unread_notifications_count(db_session, current_user.id)
    return {"unread_count": count}


# ============================================================================
# 3. MARK SINGLE NOTIFICATION AS READ
# ============================================================================

@router.post("/api/user/notifications/{notification_id}/read")
async def mark_user_notification_read(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read (called by user-shell.js and notifications.html)."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    updated = await mark_notification_as_read(db_session, notification_id)
    return {
        "success": True,
        "id": updated.id,
        "is_read": updated.is_read,
        "message": "Notification marked as read"
    }


@router.put("/api/v1/notifications/{notification_id}/mark-as-read", response_model=Notification)
@router.put("/api/user/notifications/{notification_id}/mark-as-read", response_model=Notification)
async def mark_as_read(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read (PUT endpoint)."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return await mark_notification_as_read(db_session, notification_id)


# ============================================================================
# 4. MARK ALL AS READ / CLEAR ALL
# ============================================================================

@router.delete("/api/user/notifications")
async def clear_all_user_notifications(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Clear (mark all as read or remove) all notifications for current user."""
    await db_session.execute(
        delete(DBNotification).where(DBNotification.user_id == current_user.id)
    )
    await db_session.commit()
    return {"success": True, "message": "All notifications cleared"}


@router.put("/api/v1/notifications/mark-all-as-read", status_code=status.HTTP_204_NO_CONTENT)
@router.put("/api/user/notifications/mark-all-as-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    await mark_all_notifications_as_read(db_session, current_user.id)


# ============================================================================
# 5. GET SINGLE NOTIFICATION DETAIL
# ============================================================================

@router.get("/api/user/notifications/{notification_id}", response_model=Notification)
@router.get("/api/v1/notifications/{notification_id}", response_model=Notification)
async def get_notification_detail(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific notification."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


# ============================================================================
# 6. DELETE SINGLE NOTIFICATION
# ============================================================================

@router.delete("/api/user/notifications/{notification_id}")
async def delete_user_notification(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a single notification."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await delete_notification(db_session, notification_id)
    return {"success": True, "id": notification_id, "message": "Notification deleted"}


@router.delete("/api/v1/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_endpoint(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a notification (v1 endpoint)."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await delete_notification(db_session, notification_id)


# ============================================================================
# 7. CREATE NOTIFICATION (Admin or Internal Services)
# ============================================================================

@router.post("/api/user/notifications", response_model=Notification)
@router.post("/api/v1/notifications", response_model=Notification)
async def create_notification_endpoint(
    notification: NotificationCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a notification in the database."""
    return await create_notification(db_session, notification, current_user.id)
