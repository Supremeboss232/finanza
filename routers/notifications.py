"""Notification API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
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

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=List[Notification])
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all notifications for the current user."""
    return await get_user_notifications(db_session, current_user.id, skip, limit)

@router.get("/unread/count", response_model=dict)
async def get_unread_count(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications."""
    count = await get_unread_notifications_count(db_session, current_user.id)
    return {"unread_count": count}

@router.post("", response_model=Notification)
async def create_notification_endpoint(
    notification: NotificationCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a notification (admin only, but authenticated users can use this endpoint)."""
    return await create_notification(db_session, notification, current_user.id)

@router.get("/{notification_id}", response_model=Notification)
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

@router.put("/{notification_id}/mark-as-read", response_model=Notification)
async def mark_as_read(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return await mark_notification_as_read(db_session, notification_id)

@router.put("/mark-all-as-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    await mark_all_notifications_as_read(db_session, current_user.id)

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_endpoint(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    notification = await get_notification(db_session, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await delete_notification(db_session, notification_id)
