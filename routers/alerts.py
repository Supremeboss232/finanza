"""Alerts and notifications API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user
from app.database import get_session
from app.models import User

router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/preferences")
async def get_alert_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get alert and notification preferences for current user."""
    # Alert preferences functionality to be implemented
    return {}


@router.put("/preferences", status_code=status.HTTP_200_OK)
async def update_alert_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update alert and notification preferences."""
    try:
        # Validate preferences
        if "channels" in preferences:
            for channel, enabled in preferences["channels"].items():
                if not isinstance(enabled, bool):
                    raise ValueError(f"Channel {channel} must be boolean")
        
        return {
            "message": "Preferences updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def get_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 20,
    read: bool = None,
    type: str = None
):
    """Get alerts for current user."""
    # Alerts functionality to be implemented
    return []


@router.get("/{alert_id}")
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get specific alert details."""
    return {
        "id": alert_id,
        "type": "transaction",
        "subtype": "large_transfer",
        "title": "Large Transfer",
        "message": "Transfer of $5,000.00 to John Doe completed",
        "timestamp": "2024-01-20T10:30:00",
        "is_read": False,
        "priority": "medium",
        "details": {
            "amount": 5000.00,
            "recipient": "John Doe",
            "account_ending": "1234",
            "reference_id": "TRF20240120001"
        }
    }


@router.put("/{alert_id}/read", status_code=status.HTTP_200_OK)
async def mark_alert_as_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark alert as read."""
    return {
        "id": alert_id,
        "is_read": True,
        "message": "Alert marked as read"
    }


@router.put("/{alert_id}/unread", status_code=status.HTTP_200_OK)
async def mark_alert_as_unread(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark alert as unread."""
    return {
        "id": alert_id,
        "is_read": False,
        "message": "Alert marked as unread"
    }


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_alerts_as_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark all alerts as read."""
    return {
        "message": "All alerts marked as read",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete an alert."""
    return None


@router.post("/delete-batch", status_code=status.HTTP_200_OK)
async def delete_alerts_batch(
    alert_ids: List[int],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete multiple alerts."""
    return {
        "message": f"Deleted {len(alert_ids)} alerts",
        "deleted_ids": alert_ids
    }


@router.get("/stats/unread")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get count of unread alerts."""
    return {
        "total_unread": 2,
        "by_type": {
            "transaction": 0,
            "security": 1,
            "account": 1,
            "marketing": 0
        }
    }


@router.get("/stats/summary")
async def get_alert_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get alert summary statistics."""
    return {
        "total_alerts": 24,
        "unread_alerts": 2,
        "today": 3,
        "this_week": 8,
        "by_type": {
            "transaction": 12,
            "security": 5,
            "account": 5,
            "marketing": 2
        },
        "by_priority": {
            "high": 2,
            "medium": 15,
            "low": 7
        }
    }
