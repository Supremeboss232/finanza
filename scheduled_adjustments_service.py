"""
Scheduled Balance Adjustments Service
Manages recurring and scheduled balance adjustments
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class ScheduledAdjustmentStatus:
    """Status constants for scheduled adjustments"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecurrencePattern:
    """Recurrence pattern constants"""
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ScheduledBalanceAdjustmentsService:
    """
    Manage scheduled and recurring balance adjustments
    Allows admins to schedule balance changes for future execution
    """
    
    def __init__(self):
        pass
    
    async def create_scheduled_adjustment(
        self,
        db: AsyncSession,
        user_id: str,
        amount: Decimal,
        reason: str,
        scheduled_for: datetime,
        recurrence: str = RecurrencePattern.ONCE,
        recurrence_end: Optional[datetime] = None,
        admin_id: str = None,
        notes: str = None,
    ) -> dict:
        """
        Create a scheduled balance adjustment
        
        Args:
            user_id: Target user ID
            amount: Amount to adjust (positive for credit, negative for debit)
            reason: Reason for adjustment
            scheduled_for: When to execute
            recurrence: ONCE, DAILY, WEEKLY, MONTHLY, QUARTERLY
            recurrence_end: When recurring adjustments stop
            admin_id: Admin creating the schedule
            notes: Additional notes
        
        Returns:
            Scheduled adjustment details
        """
        from models import User, ScheduledAdjustment
        
        try:
            # Verify user exists
            user_stmt = select(User).where(User.id == user_id)
            user = await db.scalar(user_stmt)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create scheduled adjustment record
            adjustment = ScheduledAdjustment(
                user_id=user_id,
                amount=amount,
                reason=reason,
                scheduled_for=scheduled_for,
                recurrence=recurrence,
                recurrence_end=recurrence_end,
                created_by=admin_id,
                status=ScheduledAdjustmentStatus.PENDING,
                notes=notes,
                created_at=datetime.utcnow(),
            )
            
            db.add(adjustment)
            await db.commit()
            
            logger.info(
                f"Scheduled adjustment created: {adjustment.id} "
                f"for user {user_id}, amount {amount}, scheduled for {scheduled_for}"
            )
            
            return {
                'id': adjustment.id,
                'user_id': adjustment.user_id,
                'amount': str(adjustment.amount),
                'reason': adjustment.reason,
                'scheduled_for': adjustment.scheduled_for.isoformat(),
                'recurrence': adjustment.recurrence,
                'status': adjustment.status,
                'created_at': adjustment.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create scheduled adjustment: {e}")
            raise
    
    async def execute_due_adjustments(self, db: AsyncSession) -> int:
        """
        Execute all due scheduled adjustments
        Called periodically (e.g., every hour)
        
        Returns:
            Number of adjustments executed
        """
        from models import ScheduledAdjustment, Ledger
        from balance_service import get_balance_service
        
        balance_service = get_balance_service()
        executed_count = 0
        
        try:
            # Get all pending adjustments due for execution
            now = datetime.utcnow()
            stmt = select(ScheduledAdjustment).where(
                (ScheduledAdjustment.status == ScheduledAdjustmentStatus.PENDING) &
                (ScheduledAdjustment.scheduled_for <= now)
            )
            
            result = await db.execute(stmt)
            adjustments = result.scalars().all()
            
            for adjustment in adjustments:
                try:
                    # Execute the balance adjustment
                    ledger_entry = await balance_service.adjust_balance(
                        db=db,
                        user_id=adjustment.user_id,
                        amount=adjustment.amount,
                        reason=adjustment.reason,
                        admin_id=adjustment.created_by,
                        notes=f"Scheduled: {adjustment.notes}" if adjustment.notes else "Scheduled adjustment",
                    )
                    
                    # Update adjustment status
                    if adjustment.recurrence == RecurrencePattern.ONCE:
                        adjustment.status = ScheduledAdjustmentStatus.EXECUTED
                        adjustment.executed_at = now
                    else:
                        # Schedule next occurrence
                        adjustment.last_executed = now
                        next_scheduled = self._calculate_next_execution(
                            adjustment.scheduled_for,
                            adjustment.recurrence,
                            adjustment.recurrence_end
                        )
                        if next_scheduled and next_scheduled <= adjustment.recurrence_end:
                            adjustment.scheduled_for = next_scheduled
                        else:
                            adjustment.status = ScheduledAdjustmentStatus.EXECUTED
                    
                    await db.commit()
                    executed_count += 1
                    logger.info(f"Executed scheduled adjustment {adjustment.id}")
                    
                except Exception as e:
                    adjustment.status = ScheduledAdjustmentStatus.FAILED
                    adjustment.error_message = str(e)
                    await db.commit()
                    logger.error(f"Failed to execute adjustment {adjustment.id}: {e}")
            
            return executed_count
        
        except Exception as e:
            logger.error(f"Error in execute_due_adjustments: {e}")
            return 0
    
    def _calculate_next_execution(
        self,
        current: datetime,
        recurrence: str,
        end_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate next execution datetime based on recurrence pattern"""
        
        if recurrence == RecurrencePattern.ONCE:
            return None
        elif recurrence == RecurrencePattern.DAILY:
            next_exec = current + timedelta(days=1)
        elif recurrence == RecurrencePattern.WEEKLY:
            next_exec = current + timedelta(weeks=1)
        elif recurrence == RecurrencePattern.MONTHLY:
            if current.month == 12:
                next_exec = current.replace(year=current.year + 1, month=1)
            else:
                next_exec = current.replace(month=current.month + 1)
        elif recurrence == RecurrencePattern.QUARTERLY:
            month = current.month + 3
            year = current.year
            if month > 12:
                month -= 12
                year += 1
            next_exec = current.replace(month=month, year=year)
        else:
            return None
        
        # Check if beyond end date
        if end_date and next_exec > end_date:
            return None
        
        return next_exec
    
    async def cancel_scheduled_adjustment(
        self,
        db: AsyncSession,
        adjustment_id: str,
        reason: str = None
    ) -> bool:
        """Cancel a pending scheduled adjustment"""
        from models import ScheduledAdjustment
        
        try:
            stmt = select(ScheduledAdjustment).where(ScheduledAdjustment.id == adjustment_id)
            adjustment = await db.scalar(stmt)
            
            if not adjustment:
                logger.warning(f"Adjustment {adjustment_id} not found")
                return False
            
            if adjustment.status != ScheduledAdjustmentStatus.PENDING:
                logger.warning(f"Cannot cancel adjustment {adjustment_id} - status is {adjustment.status}")
                return False
            
            adjustment.status = ScheduledAdjustmentStatus.CANCELLED
            adjustment.cancellation_reason = reason
            await db.commit()
            
            logger.info(f"Cancelled scheduled adjustment {adjustment_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to cancel adjustment: {e}")
            return False
    
    async def list_scheduled_adjustments(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """List scheduled adjustments with filters"""
        from models import ScheduledAdjustment
        
        try:
            stmt = select(ScheduledAdjustment)
            
            if user_id:
                stmt = stmt.where(ScheduledAdjustment.user_id == user_id)
            if status:
                stmt = stmt.where(ScheduledAdjustment.status == status)
            
            stmt = stmt.order_by(ScheduledAdjustment.scheduled_for).limit(limit)
            
            result = await db.execute(stmt)
            adjustments = result.scalars().all()
            
            return [
                {
                    'id': a.id,
                    'user_id': a.user_id,
                    'amount': str(a.amount),
                    'reason': a.reason,
                    'scheduled_for': a.scheduled_for.isoformat(),
                    'recurrence': a.recurrence,
                    'status': a.status,
                    'created_at': a.created_at.isoformat(),
                    'created_by': a.created_by,
                }
                for a in adjustments
            ]
        except Exception as e:
            logger.error(f"Failed to list scheduled adjustments: {e}")
            return []


# Singleton instance
_scheduled_service: Optional[ScheduledBalanceAdjustmentsService] = None


def get_scheduled_adjustments_service() -> ScheduledBalanceAdjustmentsService:
    """Get or create scheduled adjustments service"""
    global _scheduled_service
    if _scheduled_service is None:
        _scheduled_service = ScheduledBalanceAdjustmentsService()
    return _scheduled_service
