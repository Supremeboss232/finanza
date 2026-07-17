"""
Audit API v1 Router - Dashboard Session Audit Endpoints
Handles: dashboard session audit logging, user activity tracking
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import List, Optional
from datetime import datetime

from deps import SessionDep

# ==================== SCHEMAS ====================
class DashboardAction(BaseModel):
    """Single action logged during dashboard session"""
    action: str
    component: Optional[str] = None
    timestamp: str
    details: Optional[dict] = None

class DashboardSessionPayload(BaseModel):
    """Dashboard session audit payload from frontend"""
    actions: List[DashboardAction]
    sessionStartTime: int
    sessionDuration: int

# ==================== ROUTER ====================
audit_v1_router = APIRouter(prefix="/api/v1/audit", tags=["audit_v1"])

@audit_v1_router.post("/dashboard-session")
async def log_dashboard_session(
    payload: DashboardSessionPayload,
    db_session: SessionDep
):
    """
    Log dashboard session audit data from frontend.
    
    Records:
    - List of user actions during session
    - Session start time and total duration
    - Timestamps and component info for each action
    
    Used to track user behavior on dashboards for security and UX analysis.
    """
    try:
        log_instance = logging.getLogger(__name__)
        
        # Format session info
        session_start = datetime.fromtimestamp(payload.sessionStartTime / 1000).isoformat()
        session_duration_sec = payload.sessionDuration / 1000
        action_count = len(payload.actions)
        
        # Log aggregated session info
        log_instance.info(
            f"📊 DASHBOARD SESSION | "
            f"Start: {session_start} | "
            f"Duration: {session_duration_sec:.2f}s | "
            f"Actions: {action_count}"
        )
        
        # Log each action for detailed audit trail
        for action in payload.actions:
            action_details = f" ({action.component})" if action.component else ""
            details_str = f" - {action.details}" if action.details else ""
            log_instance.debug(
                f"  📍 {action.action}{action_details} | {action.timestamp}{details_str}"
            )
        
        return {
            "success": True,
            "message": "Dashboard session audit logged",
            "actions_recorded": action_count
        }
        
    except Exception as e:
        log_instance = logging.getLogger(__name__)
        log_instance.error(
            f"❌ Error logging dashboard session: {e}",
            exc_info=True
        )
        # Don't raise error - audit logging should not block user flow
        return {
            "success": False,
            "message": "Dashboard session audit logging failed (non-critical)"
        }
