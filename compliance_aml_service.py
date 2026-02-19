"""
Compliance & AML Service - Sanctions screening, transaction monitoring, SAR filing
"""

from datetime import datetime, date
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from models import (
    User, Transaction, TransactionMonitoring, SanctionsCheck, SAR,
    KYCReverification
)
import logging
import json

log = logging.getLogger(__name__)


class SanctionsScreeningService:
    """OFAC and sanctions list screening"""
    
    @staticmethod
    async def screen_user(db: Session, user_id: int, full_name: str) -> Dict:
        """
        Screen user against sanctions lists
        Sources: OFAC, UN, EU, UK
        """
        try:
            # Check if already screened recently
            recent_check = db.query(SanctionsCheck).filter(
                SanctionsCheck.user_id == user_id
            ).order_by(SanctionsCheck.check_date.desc()).first()
            
            if recent_check:
                # If checked within 30 days and clear, return
                days_since = (datetime.utcnow() - recent_check.check_date).days
                if days_since < 30 and recent_check.status == "clear":
                    return {
                        "success": True,
                        "status": "clear",
                        "cached": True
                    }
            
            # Perform screening against OFAC, UN, EU lists
            # TODO: Call actual screening APIs
            match_score = await SanctionsScreeningService.check_ofac(full_name)
            
            # Determine status based on match score
            if match_score > 0.95:
                status = "confirmed_match"
                action = "block"
            elif match_score > 0.85:
                status = "possible_match"
                action = "manual_review"
            else:
                status = "clear"
                action = "allow"
            
            # Record screening
            check = SanctionsCheck(
                user_id=user_id,
                full_name=full_name,
                source="ofac",  # TODO: Check all sources
                match_score=match_score,
                status=status,
                action_taken=action
            )
            db.add(check)
            db.commit()
            
            log.info(f"Sanctions screening for user {user_id}: {status} (score: {match_score})")
            return {
                "success": True,
                "status": status,
                "match_score": match_score,
                "action": action
            }
        except Exception as e:
            log.error(f"Error screening sanctions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_ofac(full_name: str) -> float:
        """
        Check against OFAC list
        Returns match score (0.0 to 1.0)
        """
        try:
            # TODO: Call actual OFAC API or download database
            # For now, return mock score
            name_lower = full_name.lower()
            
            # Mock blocked names
            blocked_names = [
                "putin", "xi jinping", "kim jong", "maduro", "hassan nasrallah"
            ]
            
            for blocked in blocked_names:
                if blocked in name_lower:
                    return 0.99
            
            # Check name complexity and format
            name_parts = name_lower.split()
            if len(name_parts) < 2:
                return 0.1  # Single name is common
            
            return 0.05  # Default low score
        except Exception as e:
            log.error(f"Error checking OFAC: {str(e)}")
            return 0.0


class TransactionMonitoringService:
    """Real-time transaction monitoring for AML compliance"""
    
    # Risk scoring thresholds
    CRITICAL_THRESHOLD = 80.0
    HIGH_THRESHOLD = 60.0
    MEDIUM_THRESHOLD = 40.0
    
    @staticmethod
    async def monitor_transaction(
        db: Session,
        transaction_id: int,
        user_id: int,
        amount: float
    ) -> Dict:
        """
        Monitor transaction for suspicious activity
        Returns risk score and action
        """
        try:
            # Calculate risk score based on rules
            risk_score = 0.0
            triggered_rules = []
            
            # Rule 1: High amount
            if amount > 10000:
                risk_score += 30.0
                triggered_rules.append("high_amount")
            
            # Rule 2: Velocity check
            velocity_score = await TransactionMonitoringService.check_velocity(db, user_id)
            risk_score += velocity_score
            if velocity_score > 0:
                triggered_rules.append("high_velocity")
            
            # Rule 3: Unusual pattern
            pattern_score = await TransactionMonitoringService.check_pattern(db, user_id, amount)
            risk_score += pattern_score
            if pattern_score > 0:
                triggered_rules.append("unusual_pattern")
            
            # Rule 4: Time-based checks
            if datetime.utcnow().hour >= 22 or datetime.utcnow().hour <= 6:
                risk_score += 15.0
                triggered_rules.append("unusual_time")
            
            # Determine action based on score
            if risk_score >= TransactionMonitoringService.CRITICAL_THRESHOLD:
                status = "escalated"
                action = "block"
            elif risk_score >= TransactionMonitoringService.HIGH_THRESHOLD:
                status = "escalated"
                action = "investigate"
            elif risk_score >= TransactionMonitoringService.MEDIUM_THRESHOLD:
                status = "investigated"
                action = "monitor"
            else:
                status = "cleared"
                action = "allow"
            
            # Record monitoring
            monitoring = TransactionMonitoring(
                transaction_id=transaction_id,
                user_id=user_id,
                risk_score=min(100.0, risk_score),
                rule_hits=",".join(triggered_rules),
                flags=",".join(triggered_rules),
                status=status
            )
            db.add(monitoring)
            
            # If critical, file SAR
            if action == "block":
                sar = await SARFilingService.file_sar(
                    db, user_id, [transaction_id],
                    f"Transaction {transaction_id} flagged for suspicious activity"
                )
            
            db.commit()
            log.info(f"Transaction {transaction_id} monitored: risk_score={risk_score}, action={action}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "risk_score": risk_score,
                "status": status,
                "action": action,
                "triggered_rules": triggered_rules
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error monitoring transaction: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_velocity(db: Session, user_id: int) -> float:
        """Check transaction velocity (transactions per hour/day)"""
        try:
            from datetime import timedelta
            
            # Count transactions in last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_txns = db.query(Transaction).filter(
                Transaction.sender_id == user_id,
                Transaction.created_at >= one_hour_ago
            ).count()
            
            score = 0.0
            if recent_txns > 10:
                score += 40.0  # High velocity
            elif recent_txns > 5:
                score += 20.0
            
            # Count transactions in last day
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            daily_txns = db.query(Transaction).filter(
                Transaction.sender_id == user_id,
                Transaction.created_at >= one_day_ago
            ).count()
            
            if daily_txns > 50:
                score += 20.0
            
            return min(50.0, score)
        except Exception as e:
            log.error(f"Error checking velocity: {str(e)}")
            return 0.0
    
    @staticmethod
    async def check_pattern(db: Session, user_id: int, amount: float) -> float:
        """Check for unusual transaction patterns"""
        try:
            # Get user's average transaction amount
            from sqlalchemy import func
            avg_amount = db.query(func.avg(Transaction.amount)).filter(
                Transaction.sender_id == user_id
            ).scalar() or 1000
            
            # If transaction is 3x average, flag
            if amount > avg_amount * 3:
                return 25.0
            elif amount > avg_amount * 2:
                return 10.0
            
            return 0.0
        except Exception as e:
            log.error(f"Error checking pattern: {str(e)}")
            return 0.0


class SARFilingService:
    """Suspicious Activity Report (SAR) filing"""
    
    SAR_THRESHOLD = 5000  # $5,000 threshold for filing
    
    @staticmethod
    async def file_sar(
        db: Session,
        user_id: int,
        transaction_ids: List[int],
        description: str,
        threshold_amount: float = 5000
    ) -> Dict:
        """File SAR with FinCEN"""
        try:
            # Create SAR record
            filing_id = f"SAR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{user_id}"
            
            sar = SAR(
                filing_id=filing_id,
                user_id=user_id,
                transaction_ids=",".join(map(str, transaction_ids)),
                suspicious_activity_description=description,
                threshold_amount=threshold_amount,
                filing_date=date.today(),
                status="draft"
            )
            db.add(sar)
            db.flush()
            
            # Mark transactions as having SAR filed
            for txn_id in transaction_ids:
                monitoring = db.query(TransactionMonitoring).filter(
                    TransactionMonitoring.transaction_id == txn_id
                ).first()
                if monitoring:
                    monitoring.sars_filed = True
                    monitoring.sars_id = filing_id
            
            db.commit()
            log.info(f"SAR {filing_id} filed for user {user_id}")
            
            return {
                "success": True,
                "sar_id": filing_id,
                "status": "draft"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error filing SAR: {str(e)}")
            return {"success": False, "error": str(e)}


class KYCReverificationService:
    """KYC re-verification scheduling and management"""
    
    # Annual re-verification required
    REVERIFICATION_INTERVAL_DAYS = 365
    
    @staticmethod
    async def schedule_reverification(
        db: Session,
        user_id: int,
        reason: str = "annual_review"
    ) -> Dict:
        """Schedule KYC re-verification"""
        try:
            from datetime import timedelta
            
            reverif = db.query(KYCReverification).filter(
                KYCReverification.user_id == user_id
            ).first()
            
            if reverif:
                reverif.reason = reason
                reverif.next_reverification_date = (
                    date.today() + timedelta(days=KYCReverificationService.REVERIFICATION_INTERVAL_DAYS)
                )
                reverif.status = "pending"
            else:
                reverif = KYCReverification(
                    user_id=user_id,
                    last_verified=date.today(),
                    next_reverification_date=(
                        date.today() + timedelta(days=KYCReverificationService.REVERIFICATION_INTERVAL_DAYS)
                    ),
                    reason=reason,
                    status="pending"
                )
                db.add(reverif)
            
            db.commit()
            log.info(f"KYC re-verification scheduled for user {user_id}: {reason}")
            
            return {
                "success": True,
                "next_reverification": reverif.next_reverification_date.isoformat(),
                "reason": reason
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error scheduling re-verification: {str(e)}")
            return {"success": False, "error": str(e)}
