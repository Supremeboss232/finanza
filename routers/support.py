"""Support Ticket API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep, get_current_admin_user
from models import User
from crud import (
    create_support_ticket,
    get_support_ticket,
    get_user_support_tickets,
    get_all_support_tickets,
    update_support_ticket,
    delete_support_ticket,
)
from schemas import (
    SupportTicket,
    SupportTicketCreate,
)

router = APIRouter(
    prefix="/api/v1/support",
    tags=["support"],
)

@router.post("", response_model=SupportTicket)
async def submit_ticket(
    ticket: SupportTicketCreate,
    db_session: SessionDep,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Submit a support ticket (can be anonymous or authenticated)."""
    user_id = current_user.id if current_user else None
    return await create_support_ticket(db_session, ticket, user_id)

@router.get("/my-tickets", response_model=List[SupportTicket])
async def my_tickets(
    skip: int = 0,
    limit: int = 100,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get current user's support tickets."""
    return await get_user_support_tickets(db_session, current_user.id, skip, limit)

@router.get("/{ticket_id}", response_model=SupportTicket)
async def get_ticket(
    ticket_id: int,
    db_session: SessionDep,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get a specific support ticket."""
    ticket = await get_support_ticket(db_session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    # Users can only view their own tickets, admins can view all
    if current_user and not current_user.is_admin:
        if ticket.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return ticket

# Admin endpoints

@router.get("/admin/all", response_model=List[SupportTicket])
async def admin_all_tickets(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_admin_user),
):
    """Get all support tickets (admin only)."""
    return await get_all_support_tickets(db_session, skip, limit, status_filter)

@router.put("/{ticket_id}", response_model=SupportTicket)
async def update_ticket(
    ticket_id: int,
    ticket_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_admin_user),
):
    """Update a support ticket (admin only)."""
    ticket = await get_support_ticket(db_session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    # Only allow certain fields to be updated
    allowed_fields = ["status", "priority"]
    filtered_data = {k: v for k, v in ticket_data.items() if k in allowed_fields}
    
    return await update_support_ticket(db_session, ticket_id, filtered_data)

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_admin_user),
):
    """Delete a support ticket (admin only)."""
    ticket = await get_support_ticket(db_session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    await delete_support_ticket(db_session, ticket_id)
