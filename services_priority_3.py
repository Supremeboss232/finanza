"""Business logic services for Priority 3 features."""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, time
from decimal import Decimal
from typing import List, Optional, Dict
import json
import logging
from enum import Enum

from models import (
    User, Account, Transaction
)
from models_priority_3 import (
    ScheduledTransfer, ScheduledTransferExecution, Webhook, WebhookDelivery,
    MobileDeposit, FlaggedTransaction, CountryRiskAssessment, SanctionsScreening
)

log = logging.getLogger(__name__)


class TransferFrequency(str, Enum):
    """Frequency options for transfers."""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ScheduledTransfersService:
    """Service for managing scheduled transfers."""
    
    @staticmethod
    def calculate_next_execution(
        transfer: ScheduledTransfer,
        current_execution: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate the next execution date for a transfer."""
        
        from dateutil.relativedelta import relativedelta
        
        base_date = current_execution or transfer.start_date
        frequency = transfer.frequency
        
        if frequency == TransferFrequency.ONCE:
            return None  # No next execution for one-time transfers
        
        elif frequency == TransferFrequency.DAILY:
            next_date = base_date + timedelta(days=1)
        elif frequency == TransferFrequency.WEEKLY:
            next_date = base_date + timedelta(weeks=1)
        elif frequency == TransferFrequency.MONTHLY:
            next_date = base_date + relativedelta(months=1)
        elif frequency == TransferFrequency.YEARLY:
            next_date = base_date + relativedelta(years=1)
        else:
            return None
        
        # Check if next execution is within end date
        if transfer.end_date and next_date > transfer.end_date:
            return None
        
        return next_date
    
    @staticmethod
    def check_pending_transfers(db: Session) -> List[ScheduledTransfer]:
        """Get all pending transfers ready for execution."""
        
        now = datetime.utcnow()
        
        transfers = db.query(ScheduledTransfer).filter(
            ScheduledTransfer.status == "active",
            ScheduledTransfer.start_date <= now,
            or_(
                ScheduledTransfer.end_date.is_(None),
                ScheduledTransfer.end_date >= now
            )
        ).all()
        
        return transfers
    
    @staticmethod
    def execute_transfer(
        db: Session,
        transfer: ScheduledTransfer,
        transaction: Optional[Transaction] = None
    ) -> ScheduledTransferExecution:
        """Execute a scheduled transfer."""
        
        execution = ScheduledTransferExecution(
            scheduled_transfer_id=transfer.id,
            execution_date=datetime.utcnow(),
            status="completed" if transaction else "failed",
            transaction_id=transaction.id if transaction else None,
        )
        
        if not transaction:
            execution.error_message = "Transfer execution failed"
        
        db.add(execution)
        db.flush()
        
        # Update transfer status if one-time
        if transfer.frequency == TransferFrequency.ONCE:
            transfer.status = "completed"
        
        return execution
    
    @staticmethod
    def get_user_statistics(db: Session, user_id: int) -> Dict:
        """Get transfer statistics for a user."""
        
        transfers = db.query(ScheduledTransfer.id).filter(
            ScheduledTransfer.user_id == user_id
        ).all()
        
        transfer_ids = [t[0] for t in transfers]
        
        if not transfer_ids:
            return {
                "total_scheduled": 0,
                "active": 0,
                "paused": 0,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
            }
        
        active = db.query(func.count(ScheduledTransfer.id)).filter(
            ScheduledTransfer.id.in_(transfer_ids),
            ScheduledTransfer.status == "active"
        ).scalar() or 0
        
        paused = db.query(func.count(ScheduledTransfer.id)).filter(
            ScheduledTransfer.id.in_(transfer_ids),
            ScheduledTransfer.status == "paused"
        ).scalar() or 0
        
        total_exec = db.query(func.count(ScheduledTransferExecution.id)).filter(
            ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids)
        ).scalar() or 0
        
        successful = db.query(func.count(ScheduledTransferExecution.id)).filter(
            ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids),
            ScheduledTransferExecution.status == "completed"
        ).scalar() or 0
        
        failed = db.query(func.count(ScheduledTransferExecution.id)).filter(
            ScheduledTransferExecution.scheduled_transfer_id.in_(transfer_ids),
            ScheduledTransferExecution.status == "failed"
        ).scalar() or 0
        
        return {
            "total_scheduled": len(transfer_ids),
            "active": active,
            "paused": paused,
            "total_executions": total_exec,
            "successful_executions": successful,
            "failed_executions": failed,
        }


class WebhooksService:
    """Service for managing webhooks."""
    
    @staticmethod
    def create_webhook(
        db: Session,
        user_id: int,
        name: str,
        url: str,
        events: List[str],
        **kwargs
    ) -> Webhook:
        """Create a new webhook."""
        
        webhook = Webhook(
            user_id=user_id,
            name=name,
            url=url,
            events=json.dumps(events),
            active=kwargs.get("active", True),
            retry_count=kwargs.get("retry_count", 3),
            timeout_seconds=kwargs.get("timeout_seconds", 30),
            secret_key=kwargs.get("secret_key"),
        )
        
        db.add(webhook)
        db.flush()
        
        return webhook
    
    @staticmethod
    def trigger_webhook(
        db: Session,
        webhook: Webhook,
        event_type: str,
        payload: Dict
    ) -> WebhookDelivery:
        """Create a webhook delivery record."""
        
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=json.dumps(payload),
            status="pending",
            attempt_count=0,
        )
        
        db.add(delivery)
        db.flush()
        
        return delivery
    
    @staticmethod
    def update_delivery_status(
        db: Session,
        delivery: WebhookDelivery,
        status: str,
        http_status: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> WebhookDelivery:
        """Update webhook delivery status."""
        
        delivery.status = status
        delivery.http_status = http_status
        delivery.error_message = error_message
        delivery.attempt_count += 1
        delivery.last_attempt = datetime.utcnow()
        delivery.updated_at = datetime.utcnow()
        
        # Calculate next retry time if failed
        if status == "failed" and delivery.attempt_count < 3:
            # Exponential backoff: 5 min, 15 min, 1 hour
            retry_minutes = [5, 15, 60]
            next_retry_minutes = retry_minutes[min(delivery.attempt_count - 1, 2)]
            delivery.next_retry = datetime.utcnow() + timedelta(minutes=next_retry_minutes)
        
        db.flush()
        
        return delivery
    
    @staticmethod
    def get_webhook_stats(db: Session) -> Dict:
        """Get system-wide webhook statistics."""
        
        total = db.query(func.count(Webhook.id)).scalar() or 0
        active = db.query(func.count(Webhook.id)).filter(
            Webhook.active == True
        ).scalar() or 0
        
        total_deliveries = db.query(func.count(WebhookDelivery.id)).scalar() or 0
        successful = db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.status == "success"
        ).scalar() or 0
        failed = db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.status == "failed"
        ).scalar() or 0
        pending = db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.status == "pending"
        ).scalar() or 0
        
        # Last 7 days success rate
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.created_at >= seven_days_ago
        ).count()
        recent_successful = db.query(WebhookDelivery).filter(
            WebhookDelivery.created_at >= seven_days_ago,
            WebhookDelivery.status == "success"
        ).count()
        
        success_rate = (recent_successful / recent_deliveries * 100) if recent_deliveries > 0 else 0
        
        return {
            "total_webhooks": total,
            "active_webhooks": active,
            "total_deliveries": total_deliveries,
            "successful": successful,
            "failed": failed,
            "pending": pending,
            "last_7_days_success_rate": success_rate,
        }


class MobileDepositsService:
    """Service for managing mobile deposits."""
    
    @staticmethod
    def create_deposit(
        db: Session,
        user_id: int,
        account_id: int,
        amount: Decimal,
        front_image_url: Optional[str] = None,
        back_image_url: Optional[str] = None,
    ) -> MobileDeposit:
        """Create a new mobile deposit."""
        
        deposit = MobileDeposit(
            user_id=user_id,
            account_id=account_id,
            amount=amount,
            front_image_url=front_image_url,
            back_image_url=back_image_url,
            status="pending",
        )
        
        db.add(deposit)
        db.flush()
        
        return deposit
    
    @staticmethod
    def analyze_deposit_images(deposit: MobileDeposit) -> Dict:
        """Analyze deposit images for quality and check detection."""
        
        # Mock image analysis - in production, use ML model
        return {
            "check_detected": True,
            "endorsement_found": True,
            "image_quality_score": Decimal("95.5"),
            "quality_score": Decimal("92.0"),
        }
    
    @staticmethod
    def approve_deposit(
        db: Session,
        deposit: MobileDeposit,
        reviewer_id: int,
        review_notes: Optional[str] = None
    ) -> MobileDeposit:
        """Approve a mobile deposit."""
        
        deposit.status = "approved"
        deposit.reviewed_by = reviewer_id
        deposit.review_notes = review_notes
        deposit.processed_at = datetime.utcnow()
        
        db.flush()
        
        return deposit
    
    @staticmethod
    def reject_deposit(
        db: Session,
        deposit: MobileDeposit,
        reviewer_id: int,
        review_notes: str
    ) -> MobileDeposit:
        """Reject a mobile deposit."""
        
        deposit.status = "rejected"
        deposit.reviewed_by = reviewer_id
        deposit.review_notes = review_notes
        deposit.processed_at = datetime.utcnow()
        
        db.flush()
        
        return deposit
    
    @staticmethod
    def get_deposit_stats(db: Session) -> Dict:
        """Get system-wide mobile deposit statistics."""
        
        total = db.query(func.count(MobileDeposit.id)).scalar() or 0
        pending = db.query(func.count(MobileDeposit.id)).filter(
            MobileDeposit.status == "pending"
        ).scalar() or 0
        approved = db.query(func.count(MobileDeposit.id)).filter(
            MobileDeposit.status == "approved"
        ).scalar() or 0
        rejected = db.query(func.count(MobileDeposit.id)).filter(
            MobileDeposit.status == "rejected"
        ).scalar() or 0
        
        # Average quality score
        avg_quality = db.query(func.avg(MobileDeposit.quality_score)).filter(
            MobileDeposit.quality_score.isnot(None)
        ).scalar() or 0
        
        # Last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        total_30d = db.query(func.count(MobileDeposit.id)).filter(
            MobileDeposit.created_at >= thirty_days_ago
        ).scalar() or 0
        
        total_amount_30d = db.query(func.sum(MobileDeposit.amount)).filter(
            MobileDeposit.created_at >= thirty_days_ago
        ).scalar() or 0
        
        return {
            "total_deposits": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "average_quality_score": float(avg_quality),
            "total_30d": total_30d,
            "total_amount_30d": float(total_amount_30d or 0),
        }


class ComplianceService:
    """Service for compliance and risk management."""
    
    @staticmethod
    def assess_country_risk(
        db: Session,
        country_code: str
    ) -> Optional[CountryRiskAssessment]:
        """Get country risk assessment."""
        
        assessment = db.query(CountryRiskAssessment).filter(
            CountryRiskAssessment.country_code == country_code.upper()
        ).first()
        
        return assessment
    
    @staticmethod
    def flag_transaction(
        db: Session,
        transaction_id: int,
        user_id: int,
        flag_reason: str,
        risk_score: Optional[Decimal] = None
    ) -> FlaggedTransaction:
        """Flag a transaction for compliance review."""
        
        flagged = FlaggedTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
            flag_reason=flag_reason,
            risk_score=risk_score,
            status="flagged",
        )
        
        db.add(flagged)
        db.flush()
        
        return flagged
    
    @staticmethod
    def screen_sanctions(
        db: Session,
        name: str,
        databases: Optional[List[str]] = None
    ) -> List[SanctionsScreening]:
        """Screen a name against sanctions lists."""
        
        if not databases:
            databases = ["OFAC", "UN", "EU", "UK"]
        
        screenings = []
        
        for database in databases:
            # Mock sanctions screening - in production, call external APIs
            match_found = name.lower() in ["blocked", "sanctioned", "terrorist"]
            
            screening = SanctionsScreening(
                name=name,
                screening_date=datetime.utcnow(),
                database=database,
                match_found=match_found,
                confidence_score=Decimal("95.0") if match_found else Decimal("5.0"),
            )
            
            db.add(screening)
            screenings.append(screening)
        
        db.flush()
        
        return screenings
    
    @staticmethod
    def get_compliance_report(
        db: Session,
        days: int = 30
    ) -> Dict:
        """Get compliance report for the period."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        flagged = db.query(func.count(FlaggedTransaction.id)).filter(
            FlaggedTransaction.created_at >= start_date
        ).scalar() or 0
        
        investigating = db.query(func.count(FlaggedTransaction.id)).filter(
            FlaggedTransaction.status == "investigating",
            FlaggedTransaction.created_at >= start_date
        ).scalar() or 0
        
        resolved = db.query(func.count(FlaggedTransaction.id)).filter(
            FlaggedTransaction.status == "resolved",
            FlaggedTransaction.created_at >= start_date
        ).scalar() or 0
        
        high_risk_count = db.query(func.count(FlaggedTransaction.id)).filter(
            FlaggedTransaction.risk_score >= 75,
            FlaggedTransaction.created_at >= start_date
        ).scalar() or 0
        
        sanctions_matches = db.query(func.count(SanctionsScreening.id)).filter(
            SanctionsScreening.match_found == True,
            SanctionsScreening.screening_date >= start_date
        ).scalar() or 0
        
        return {
            "total_flagged": flagged,
            "pending_investigations": investigating,
            "resolved_cases": resolved,
            "high_risk_cases": high_risk_count,
            "sanctions_matches": sanctions_matches,
            "period_days": days,
            "period_start": start_date,
            "period_end": datetime.utcnow(),
        }
