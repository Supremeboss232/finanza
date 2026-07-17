"""
Background Job Scheduler for Scheduled Balance Adjustments
===========================================================
Executes scheduled and recurring balance adjustments

Run this as a separate process or within main.py startup:
- python scheduler_worker.py (standalone)
- Or integrated via FastAPI lifespan events
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select, and_
from decimal import Decimal
import traceback

from database import Base
from models import User, ScheduledAdjustment, AuditLog
from config import settings

logger = logging.getLogger(__name__)


class ScheduledAdjustmentExecutor:
    """Executes scheduled balance adjustments"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.running = False
        self.check_interval = settings.SCHEDULER_CHECK_INTERVAL
        self.max_retries = settings.SCHEDULER_MAX_RETRIES
        self.retry_delay = settings.SCHEDULER_RETRY_DELAY
    
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.engine = create_async_engine(settings.DATABASE_URL)
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            await self.engine.begin()
            logger.info("✅ Scheduler initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize scheduler: {e}")
            raise
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info(f"🚀 Scheduler started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                await self.execute_due_adjustments()
            except Exception as e:
                logger.error(f"Scheduler error: {e}\n{traceback.format_exc()}")
            
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")
    
    async def execute_due_adjustments(self):
        """Execute all due scheduled adjustments"""
        async with self.async_session() as session:
            try:
                now = datetime.utcnow()
                
                # Find all due adjustments that haven't been executed
                stmt = select(ScheduledAdjustment).where(
                    and_(
                        ScheduledAdjustment.scheduled_for <= now,
                        ScheduledAdjustment.status == "PENDING"
                    )
                )
                
                result = await session.execute(stmt)
                adjustments = result.scalars().all()
                
                if not adjustments:
                    return
                
                logger.info(f"Found {len(adjustments)} due adjustments to execute")
                
                for adjustment in adjustments:
                    try:
                        await self._execute_adjustment(session, adjustment, now)
                    except Exception as e:
                        logger.error(f"Failed to execute adjustment {adjustment.id}: {e}")
                        adjustment.error_message = str(e)
                        adjustment.status = "FAILED"
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error in execute_due_adjustments: {e}")
                await session.rollback()
    
    async def _execute_adjustment(
        self,
        session: AsyncSession,
        adjustment: ScheduledAdjustment,
        now: datetime
    ):
        """Execute a single adjustment"""
        
        # Get the user
        user_stmt = select(User).where(User.id == adjustment.user_id)
        user = await session.scalar(user_stmt)
        
        if not user:
            raise ValueError(f"User {adjustment.user_id} not found")
        
        # Apply the balance adjustment
        old_balance = user.balance or Decimal("0")
        new_balance = old_balance + adjustment.amount
        
        if new_balance < 0:
            raise ValueError(f"Insufficient balance: {old_balance} + {adjustment.amount} = {new_balance}")
        
        user.balance = new_balance
        user.updated_at = now
        
        # Create audit log entry
        audit = AuditLog(
            action_type="SCHEDULED_ADJUSTMENT_EXECUTED",
            admin_id=adjustment.created_by,
            user_id=adjustment.user_id,
            resource_type="ScheduledAdjustment",
            resource_id=str(adjustment.id),
            details=f"Amount: {adjustment.amount}, Reason: {adjustment.reason}, Old Balance: {old_balance}, New Balance: {new_balance}"
        )
        session.add(audit)
        
        # Update adjustment status
        adjustment.status = "EXECUTED"
        adjustment.executed_at = now
        
        # Handle recurrence
        if adjustment.recurrence != "ONCE":
            await self._schedule_next_recurrence(adjustment, now)
        
        logger.info(f"✅ Executed adjustment {adjustment.id}: {adjustment.amount} for user {user.id}")
    
    async def _schedule_next_recurrence(
        self,
        adjustment: ScheduledAdjustment,
        now: datetime
    ):
        """Schedule next recurrence of adjustment"""
        
        if adjustment.recurrence_end and now >= adjustment.recurrence_end:
            logger.info(f"Recurrence ended for adjustment {adjustment.id}")
            return
        
        next_execution = now
        
        if adjustment.recurrence == "DAILY":
            next_execution = now + timedelta(days=1)
        elif adjustment.recurrence == "WEEKLY":
            next_execution = now + timedelta(weeks=1)
        elif adjustment.recurrence == "MONTHLY":
            # Add month (simplified - doesn't handle month boundaries perfectly)
            try:
                next_month = now.replace(month=now.month + 1)
            except ValueError:
                next_month = now.replace(year=now.year + 1, month=1)
            next_execution = next_month
        elif adjustment.recurrence == "QUARTERLY":
            try:
                next_quarter = now.replace(month=now.month + 3)
            except ValueError:
                next_quarter = now.replace(year=now.year + 1, month=(now.month + 3) % 12)
            next_execution = next_quarter
        
        # Create new scheduled adjustment for next execution
        from models import ScheduledAdjustment as SA_Model
        
        next_adjustment = SA_Model(
            user_id=adjustment.user_id,
            amount=adjustment.amount,
            reason=adjustment.reason,
            scheduled_for=next_execution,
            recurrence=adjustment.recurrence,
            recurrence_end=adjustment.recurrence_end,
            created_by=adjustment.created_by,
            status="PENDING",
            notes=f"Auto-recurring from {adjustment.id}"
        )
        
        logger.info(f"📅 Scheduled next recurrence: {next_adjustment.scheduled_for}")


async def run_scheduler():
    """Run the scheduler"""
    executor = ScheduledAdjustmentExecutor()
    await executor.initialize()
    await executor.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler())
