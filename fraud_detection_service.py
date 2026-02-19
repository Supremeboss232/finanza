"""
Fraud Detection Service - Real-time fraud detection and prevention
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from models import (
    Transaction, FraudScore, FraudRule, BlockedTransaction,
    DeviceFingerprint, User
)
import logging

log = logging.getLogger(__name__)


class FraudDetectionService:
    """Main fraud detection service"""
    
    # Risk levels
    CRITICAL_SCORE = 80.0
    HIGH_SCORE = 60.0
    MEDIUM_SCORE = 40.0
    
    @staticmethod
    async def evaluate_transaction(
        db: Session,
        transaction_id: int,
        user_id: int,
        amount: float,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict:
        """
        Evaluate transaction for fraud risk
        Returns: risk score, decision (approve/challenge/block)
        """
        try:
            transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Run all fraud rules
            rule_results = []
            score = 0.0
            
            # Get active rules
            rules = db.query(FraudRule).filter(FraudRule.enabled == True).all()
            
            for rule in rules:
                triggered, points = await FraudDetectionService.evaluate_rule(
                    db, user_id, amount, rule, ip_address, device_id
                )
                if triggered:
                    rule_results.append(rule.id)
                    score += points
            
            # Normalize score to 0-100
            score = min(100.0, score)
            
            # Determine decision and risk level
            if score >= FraudDetectionService.CRITICAL_SCORE:
                decision = "block"
                risk_level = "critical"
            elif score >= FraudDetectionService.HIGH_SCORE:
                decision = "challenge"
                risk_level = "high"
            elif score >= FraudDetectionService.MEDIUM_SCORE:
                decision = "challenge"
                risk_level = "medium"
            else:
                decision = "approve"
                risk_level = "low"
            
            # Record fraud score
            fraud_score = FraudScore(
                transaction_id=transaction_id,
                score=score,
                risk_level=risk_level,
                triggered_rules=",".join(map(str, rule_results)),
                decision=decision
            )
            db.add(fraud_score)
            
            # Block transaction if critical
            if decision == "block":
                blocked = BlockedTransaction(
                    transaction_id=transaction_id,
                    reason=f"Fraud risk score: {score}",
                    blocked_at=datetime.utcnow(),
                    review_status="pending"
                )
                db.add(blocked)
                transaction.status = "blocked"
            
            db.commit()
            log.info(f"Transaction {transaction_id} evaluated: score={score}, decision={decision}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "fraud_score": score,
                "risk_level": risk_level,
                "decision": decision,
                "triggered_rules": rule_results
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error evaluating transaction: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def evaluate_rule(
        db: Session,
        user_id: int,
        amount: float,
        rule: FraudRule,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> tuple:
        """
        Evaluate single fraud rule
        Returns: (triggered: bool, points: float)
        """
        try:
            if rule.rule_type == "velocity":
                return await FraudDetectionService.check_velocity_rule(db, user_id)
            elif rule.rule_type == "amount":
                return await FraudDetectionService.check_amount_rule(db, user_id, amount)
            elif rule.rule_type == "location":
                return await FraudDetectionService.check_location_rule(db, user_id, ip_address)
            elif rule.rule_type == "pattern":
                return await FraudDetectionService.check_pattern_rule(db, user_id, amount)
            else:
                return False, 0.0
        except Exception as e:
            log.error(f"Error evaluating rule {rule.id}: {str(e)}")
            return False, 0.0
    
    @staticmethod
    async def check_velocity_rule(db: Session, user_id: int) -> tuple:
        """Check velocity (transactions per hour)"""
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            count = db.query(Transaction).filter(
                Transaction.sender_id == user_id,
                Transaction.created_at >= one_hour_ago,
                Transaction.status.in_(["completed", "pending"])
            ).count()
            
            # More than 5 transactions per hour is suspicious
            if count > 10:
                return True, 30.0
            elif count > 5:
                return True, 15.0
            return False, 0.0
        except Exception as e:
            log.error(f"Error checking velocity: {str(e)}")
            return False, 0.0
    
    @staticmethod
    async def check_amount_rule(db: Session, user_id: int, current_amount: float) -> tuple:
        """Check for unusual transaction amounts"""
        try:
            from sqlalchemy import func
            
            # Get user's average and max amounts
            avg_amount = db.query(func.avg(Transaction.amount)).filter(
                Transaction.sender_id == user_id
            ).scalar() or 1000
            
            max_amount = db.query(func.max(Transaction.amount)).filter(
                Transaction.sender_id == user_id
            ).scalar() or 10000
            
            # If 5x average or 2x max, flag
            if current_amount > avg_amount * 5:
                return True, 40.0
            elif current_amount > max(avg_amount * 3, max_amount * 2):
                return True, 25.0
            return False, 0.0
        except Exception as e:
            log.error(f"Error checking amount: {str(e)}")
            return False, 0.0
    
    @staticmethod
    async def check_location_rule(db: Session, user_id: int, ip_address: Optional[str]) -> tuple:
        """Check for impossible travel / new location"""
        try:
            if not ip_address:
                return False, 0.0
            
            # Get user's last transaction IP
            last_txn = db.query(Transaction).filter(
                Transaction.sender_id == user_id
            ).order_by(Transaction.created_at.desc()).first()
            
            if last_txn and last_txn.ip_address and last_txn.ip_address != ip_address:
                # Different IP - check if device is known
                device = db.query(DeviceFingerprint).filter(
                    DeviceFingerprint.last_seen_ip == ip_address
                ).first()
                
                if not device:
                    return True, 20.0  # New location/device
            
            return False, 0.0
        except Exception as e:
            log.error(f"Error checking location: {str(e)}")
            return False, 0.0
    
    @staticmethod
    async def check_pattern_rule(db: Session, user_id: int, amount: float) -> tuple:
        """Check for unusual patterns vs user's history"""
        try:
            # Get user's typical transaction times and amounts
            from sqlalchemy import func
            
            # If user typically makes small transactions, large one is suspicious
            avg_amount = db.query(func.avg(Transaction.amount)).filter(
                Transaction.sender_id == user_id
            ).scalar() or 1000
            
            std_dev = db.query(func.stddev(Transaction.amount)).filter(
                Transaction.sender_id == user_id
            ).scalar() or avg_amount * 0.5
            
            # More than 2 standard deviations = unusual
            z_score = (amount - avg_amount) / max(std_dev, 1)
            if z_score > 2:
                return True, 15.0
            
            return False, 0.0
        except Exception as e:
            log.error(f"Error checking pattern: {str(e)}")
            return False, 0.0
    
    @staticmethod
    async def create_default_rules(db: Session) -> Dict:
        """Create default fraud detection rules"""
        try:
            rules = [
                FraudRule(
                    rule_name="High_Velocity",
                    rule_type="velocity",
                    description="More than 10 transactions in 1 hour"
                ),
                FraudRule(
                    rule_name="Unusual_Amount",
                    rule_type="amount",
                    description="Transaction amount 5x user average"
                ),
                FraudRule(
                    rule_name="New_Location",
                    rule_type="location",
                    description="Transaction from new device/IP"
                ),
                FraudRule(
                    rule_name="Anomalous_Pattern",
                    rule_type="pattern",
                    description="Transaction pattern differs from history"
                )
            ]
            
            for rule in rules:
                existing = db.query(FraudRule).filter(
                    FraudRule.rule_name == rule.rule_name
                ).first()
                if not existing:
                    db.add(rule)
            
            db.commit()
            log.info("Default fraud rules created")
            return {"success": True, "rules_created": len(rules)}
        except Exception as e:
            db.rollback()
            log.error(f"Error creating default rules: {str(e)}")
            return {"success": False, "error": str(e)}


class DeviceFingerprintService:
    """Device tracking for fraud prevention"""
    
    @staticmethod
    async def register_device(
        db: Session,
        user_id: int,
        device_id: str,
        device_name: Optional[str] = None,
        device_os: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict:
        """Register/update device fingerprint"""
        try:
            device = db.query(DeviceFingerprint).filter(
                DeviceFingerprint.device_id == device_id,
                DeviceFingerprint.user_id == user_id
            ).first()
            
            if device:
                device.last_seen_at = datetime.utcnow()
                device.last_seen_ip = ip_address
                device.last_seen_location = location
            else:
                device = DeviceFingerprint(
                    user_id=user_id,
                    device_id=device_id,
                    device_name=device_name,
                    device_os=device_os,
                    last_seen_ip=ip_address,
                    last_seen_location=location
                )
                db.add(device)
            
            db.commit()
            log.info(f"Device {device_id} registered for user {user_id}")
            return {"success": True, "device_id": device_id}
        except Exception as e:
            db.rollback()
            log.error(f"Error registering device: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def is_known_device(db: Session, user_id: int, device_id: str) -> bool:
        """Check if device is known to user"""
        try:
            device = db.query(DeviceFingerprint).filter(
                DeviceFingerprint.user_id == user_id,
                DeviceFingerprint.device_id == device_id
            ).first()
            return device is not None
        except Exception as e:
            log.error(f"Error checking device: {str(e)}")
            return False


# Alias for backward compatibility with imports expecting FraudDetectionEngine
FraudDetectionEngine = FraudDetectionService

# Additional aliases for other expected classes
class BehavioralAnalyzer(FraudDetectionService):
    """Behavioral analysis for fraud detection (alias)"""
    pass

class TransactionValidator(FraudDetectionService):
    """Transaction validation (alias)"""
    pass

class RiskScorer(FraudDetectionService):
    """Risk scoring for fraud detection (alias)"""
    pass
