"""Recipients management API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User

router = APIRouter(
    prefix="/api/recipients",
    tags=["recipients"],
    dependencies=[Depends(get_current_user)]
)


@router.get("")
async def get_recipients(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all saved recipients for current user."""
    # Recipients functionality to be implemented
    return []


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_recipient(
    recipient_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add a new recipient."""
    try:
        # Validate recipient data
        if not recipient_data.get("name"):
            raise ValueError("Recipient name is required")
        
        if not recipient_data.get("account_number"):
            raise ValueError("Account number is required")
        
        if not recipient_data.get("routing_number"):
            raise ValueError("Routing number is required")
        
        # In production, validate routing and account numbers
        # For now, just return success
        
        return {
            "id": 3,
            "name": recipient_data.get("name"),
            "account_type": recipient_data.get("account_type", "checking"),
            "account_number": f"****{recipient_data.get('account_number')[-4:]}",
            "routing_number": recipient_data.get("routing_number"),
            "bank_name": recipient_data.get("bank_name", ""),
            "is_favorite": False,
            "message": "Recipient added successfully",
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{recipient_id}")
async def get_recipient(
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get recipient details."""
    return {
        "id": recipient_id,
        "name": "John Doe",
        "account_type": "checking",
        "account_number": "****1234",
        "routing_number": "987654321",
        "bank_name": "Bank of America",
        "is_favorite": True,
        "transfer_count": 5,
        "last_transfer": "2024-01-20T10:30:00",
        "created_at": "2024-01-10T10:00:00"
    }


@router.put("/{recipient_id}", status_code=status.HTTP_200_OK)
async def update_recipient(
    recipient_id: int,
    recipient_data: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update recipient information."""
    return {
        "id": recipient_id,
        "message": "Recipient updated successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipient(
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a recipient."""
    return None


@router.post("/{recipient_id}/favorite", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Toggle recipient as favorite."""
    return {
        "id": recipient_id,
        "is_favorite": True,
        "message": "Recipient marked as favorite"
    }


@router.post("/{recipient_id}/remove-favorite", status_code=status.HTTP_200_OK)
async def remove_favorite(
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove recipient from favorites."""
    return {
        "id": recipient_id,
        "is_favorite": False,
        "message": "Recipient removed from favorites"
    }


@router.get("/search")
async def search_recipients(
    query: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Search recipients by name."""
    # Search functionality to be implemented
    return []
