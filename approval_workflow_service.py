"""
Multi-Admin Approval Workflow Service
Manages approval requests and workflows for high-value admin actions
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import logging
import uuid

logger = logging.getLogger(__name__)


class ApprovalStatus:
    """Approval workflow status constants"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ApprovalActionType:
    """Types of actions requiring approval"""
    BALANCE_ADJUSTMENT = "BALANCE_ADJUSTMENT"
    ADMIN_CREATION = "ADMIN_CREATION"
    ADMIN_REVOCATION = "ADMIN_REVOCATION"
    ROLE_CHANGE = "ROLE_CHANGE"
    USER_SUSPENSION = "USER_SUSPENSION"


class MultiAdminApprovalService:
    """
    Manage approval workflows for critical admin actions
    High-value actions require approval from another admin
    
    Configuration from config.py:
    - APPROVAL_ENABLED: Enable/disable approval workflows
    - APPROVALS_REQUIRED_FOR_HIGH_VALUE: Number of approvals needed (default: 2)
    - APPROVAL_THRESHOLD_BALANCE_ADJUSTMENT: Amount threshold (default: $10,000)
    - APPROVAL_THRESHOLD_ADMIN_CREATION: Require approval (default: True)
    - APPROVAL_THRESHOLD_ADMIN_REVOCATION: Require approval (default: True)
    - APPROVAL_EXPIRY_HOURS: Expiry time (default: 24)
    - APPROVAL_SELF_APPROVAL_PREVENTED: Prevent self-approval (default: True)
    """
    
    def __init__(self):
        """Initialize service with settings from config"""
        from config import settings
        
        # Get approval thresholds from settings (with fallback defaults)
        self.APPROVAL_ENABLED = settings.APPROVAL_ENABLED
        self.APPROVALS_REQUIRED = settings.APPROVALS_REQUIRED_FOR_HIGH_VALUE
        self.APPROVAL_EXPIRY_HOURS = settings.APPROVAL_EXPIRY_HOURS
        self.SELF_APPROVAL_PREVENTED = settings.APPROVAL_SELF_APPROVAL_PREVENTED
        
        # Thresholds requiring approval (from config)
        self.APPROVAL_THRESHOLDS = {
            'balance_adjustment': Decimal(str(settings.APPROVAL_THRESHOLD_BALANCE_ADJUSTMENT)),
            'admin_creation': settings.APPROVAL_THRESHOLD_ADMIN_CREATION,
            'admin_revocation': settings.APPROVAL_THRESHOLD_ADMIN_REVOCATION,
            'role_change_to_super': True,  # Always require approval for SUPER_ADMIN role
        }
        
        logger.info(f"Approval service initialized: enabled={self.APPROVAL_ENABLED}, required={self.APPROVALS_REQUIRED}, expiry={self.APPROVAL_EXPIRY_HOURS}h")
    
    async def request_approval(
        self,
        db: AsyncSession,
        action_type: str,
        requested_by: str,
        data: dict,
        required_approvals: int = 2,
        deadline: Optional[datetime] = None,
    ) -> dict:
        """
        Create an approval request for a critical action
        
        Args:
            action_type: Type of action requiring approval
            requested_by: Admin making the request
            data: Action details (user_id, amount, role, etc)
            required_approvals: Number of approvals needed
            deadline: When approval expires (default: 24 hours)
        
        Returns:
            Approval request details
        """
        from models import ApprovalRequest
        
        try:
            if not deadline:
                deadline = datetime.utcnow() + timedelta(hours=self.APPROVAL_EXPIRY_HOURS)
            
            approval_id = str(uuid.uuid4())
            request = ApprovalRequest(
                id=approval_id,
                action_type=action_type,
                requested_by=requested_by,
                data=data,
                status=ApprovalStatus.PENDING,
                required_approvals=required_approvals,
                current_approvals=0,
                deadline=deadline,
                created_at=datetime.utcnow(),
            )
            
            db.add(request)
            await db.commit()
            
            logger.info(
                f"Approval request created: {approval_id} "
                f"for action {action_type} by {requested_by}"
            )
            
            return {
                'id': approval_id,
                'action_type': action_type,
                'requested_by': requested_by,
                'status': ApprovalStatus.PENDING,
                'approvals_needed': required_approvals,
                'approvals_received': 0,
                'deadline': deadline.isoformat(),
                'created_at': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise
    
    async def approve_request(
        self,
        db: AsyncSession,
        request_id: str,
        approved_by: str,
        comments: str = None,
    ) -> bool:
        """
        Approve a pending approval request
        
        Returns:
            True if request is now fully approved and ready for execution
        """
        from models import ApprovalRequest, ApprovalVote
        
        try:
            # Get request
            stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
            request = await db.scalar(stmt)
            
            if not request:
                logger.warning(f"Approval request {request_id} not found")
                return False
            
            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Request {request_id} already {request.status}")
                return False
            
            if datetime.utcnow() > request.deadline:
                request.status = ApprovalStatus.EXPIRED
                await db.commit()
                logger.warning(f"Request {request_id} has expired")
                return False
            
            if approved_by == request.requested_by:
                logger.warning(f"Cannot self-approve request {request_id}")
                return False
            
            # Record approval vote
            vote = ApprovalVote(
                id=str(uuid.uuid4()),
                request_id=request_id,
                voted_by=approved_by,
                vote='APPROVE',
                comments=comments,
                voted_at=datetime.utcnow(),
            )
            db.add(vote)
            
            # Update approval count
            request.current_approvals += 1
            request.last_voted_at = datetime.utcnow()
            
            # Check if fully approved
            if request.current_approvals >= request.required_approvals:
                request.status = ApprovalStatus.APPROVED
                request.approved_at = datetime.utcnow()
                logger.info(f"Approval request {request_id} fully approved")
            
            await db.commit()
            return True
        
        except Exception as e:
            logger.error(f"Failed to approve request: {e}")
            return False
    
    async def reject_request(
        self,
        db: AsyncSession,
        request_id: str,
        rejected_by: str,
        reason: str = None,
    ) -> bool:
        """Reject a pending approval request"""
        from models import ApprovalRequest, ApprovalVote
        
        try:
            stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
            request = await db.scalar(stmt)
            
            if not request:
                logger.warning(f"Request {request_id} not found")
                return False
            
            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Cannot reject request {request_id} - status is {request.status}")
                return False
            
            # Record rejection vote
            vote = ApprovalVote(
                id=str(uuid.uuid4()),
                request_id=request_id,
                voted_by=rejected_by,
                vote='REJECT',
                comments=reason,
                voted_at=datetime.utcnow(),
            )
            db.add(vote)
            
            # Update request status
            request.status = ApprovalStatus.REJECTED
            request.rejected_by = rejected_by
            request.rejected_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Approval request {request_id} rejected by {rejected_by}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reject request: {e}")
            return False
    
    async def get_pending_approvals(
        self,
        db: AsyncSession,
        for_admin: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Get all pending approval requests"""
        from models import ApprovalRequest
        
        try:
            stmt = select(ApprovalRequest).where(
                ApprovalRequest.status == ApprovalStatus.PENDING
            ).order_by(ApprovalRequest.created_at.desc()).limit(limit)
            
            result = await db.execute(stmt)
            requests = result.scalars().all()
            
            return [
                {
                    'id': r.id,
                    'action_type': r.action_type,
                    'requested_by': r.requested_by,
                    'data': r.data,
                    'approvals': f"{r.current_approvals}/{r.required_approvals}",
                    'deadline': r.deadline.isoformat(),
                    'created_at': r.created_at.isoformat(),
                }
                for r in requests
            ]
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []
    
    async def get_approval_history(
        self,
        db: AsyncSession,
        request_id: str,
    ) -> List[dict]:
        """Get approval votes history for a request"""
        from models import ApprovalVote
        
        try:
            stmt = select(ApprovalVote).where(
                ApprovalVote.request_id == request_id
            ).order_by(ApprovalVote.voted_at)
            
            result = await db.execute(stmt)
            votes = result.scalars().all()
            
            return [
                {
                    'voted_by': v.voted_by,
                    'vote': v.vote,
                    'comments': v.comments,
                    'voted_at': v.voted_at.isoformat(),
                }
                for v in votes
            ]
        except Exception as e:
            logger.error(f"Failed to get approval history: {e}")
            return []
    
    def should_require_approval(
        self,
        action_type: str,
        amount: Optional[Decimal] = None,
    ) -> bool:
        """Determine if action requires approval"""
        
        if action_type in self.APPROVAL_THRESHOLDS:
            threshold = self.APPROVAL_THRESHOLDS[action_type]
            
            # Boolean thresholds always require approval
            if threshold is True:
                return True
            
            # Numeric thresholds require approval if amount exceeds
            if isinstance(threshold, Decimal) and amount:
                return amount > threshold
        
        return False


# Singleton instance
_approval_service: Optional[MultiAdminApprovalService] = None


def get_approval_service() -> MultiAdminApprovalService:
    """Get or create approval service"""
    global _approval_service
    if _approval_service is None:
        _approval_service = MultiAdminApprovalService()
    return _approval_service
