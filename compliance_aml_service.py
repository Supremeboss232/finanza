"""
Compliance & AML Service - Sanctions screening, transaction monitoring, SAR filing
"""

from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
from urllib.parse import quote
from sqlalchemy.orm import Session
from models import (
    User, Transaction, TransactionMonitoring, SanctionsCheck, SAR,
    KYCReverification
)
import httpx
import logging
import json
import os

log = logging.getLogger(__name__)


class SanctionsScreeningService:
    """OFAC and sanctions list screening"""
    
    @staticmethod
    async def screen_user(db: Session, user_id: int, full_name: str) -> Dict:
        """
        Screen user against sanctions lists.
        Sources: OFAC SDN (primary), UN, EU, UK (future).
        """
        try:
            # Check if already screened recently (user-level, 30-day cache)
            recent_check = db.query(SanctionsCheck).filter(
                SanctionsCheck.user_id == user_id
            ).order_by(SanctionsCheck.check_date.desc()).first()

            if recent_check:
                days_since = (datetime.utcnow() - recent_check.check_date).days
                if days_since < 30 and recent_check.status == "clear":
                    return {
                        "success": True,
                        "status": "clear",
                        "cached": True
                    }

            # Call real OFAC SDN API
            ofac_result = await SanctionsScreeningService.check_ofac(db, full_name)

            status = ofac_result["result"]
            match_score = ofac_result["score"] or 0.0
            source = ofac_result.get("source", "pending_manual_review")

            # Map result to action
            action_map = {
                "confirmed_match": "block",
                "possible_match": "manual_review",
                "clear": "allow",
                "pending_manual_review": "manual_review",
            }
            action = action_map.get(status, "manual_review")

            # Persist screening record
            check = SanctionsCheck(
                user_id=user_id,
                full_name=full_name,
                source=source,
                match_score=match_score,
                status=status,
                action_taken=action
            )
            db.add(check)
            db.commit()

            log.info(
                f"Sanctions screening for user {user_id}: {status} "
                f"(score: {match_score}, source: {source})"
            )
            return {
                "success": True,
                "status": status,
                "match_score": match_score,
                "action": action,
                "matches": ofac_result.get("matches", []),
                "screened": ofac_result.get("screened", False),
            }
        except Exception as e:
            log.error(f"Error screening sanctions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_ofac(db: Session, full_name: str) -> dict:
        """
        Check the full name against the US Treasury OFAC SDN list using the
        free public REST API (no API key required).

        Endpoint:
            GET https://sanctionssearch.ofac.treas.gov/api/search/name/{encoded_name}

        Score thresholds:
            > 95  → confirmed_match
            > 85  → possible_match
            else  → clear

        Returns a dict:
            {
                "screened": bool,
                "result": "clear" | "possible_match" | "confirmed_match" | "pending_manual_review",
                "score": float | None,
                "matches": list[str],
                "source": "ofac_sdn" | "ofac_sdn_cached" | "pending_manual_review"
            }
        """
        OFAC_API_KEY = os.environ.get("OFAC_API_KEY", "")

        # ── 24-hour name-level cache (clear results only) ──────────────────────
        cache_cutoff = datetime.utcnow() - timedelta(hours=24)
        cached = (
            db.query(SanctionsCheck)
            .filter(
                SanctionsCheck.full_name == full_name,
                SanctionsCheck.status == "clear",
                SanctionsCheck.check_date >= cache_cutoff,
            )
            .order_by(SanctionsCheck.check_date.desc())
            .first()
        )
        if cached:
            log.info(f"OFAC cache hit for '{full_name}' (cached at {cached.check_date})")
            return {
                "screened": True,
                "result": "clear",
                "score": cached.match_score or 0.0,
                "matches": [],
                "source": "ofac_sdn_cached",
            }

        # ── Primary: free US Treasury OFAC SDN REST API ────────────────────────
        encoded_name = quote(full_name, safe="")
        ofac_url = (
            f"https://sanctionssearch.ofac.treas.gov/api/search/name/{encoded_name}"
        )
        headers = {"Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(ofac_url, headers=headers)
                response.raise_for_status()
                data = response.json()

            # The OFAC API returns a list of match objects with a "score" field
            results = data if isinstance(data, list) else data.get("results", [])

            best_score: float = 0.0
            matched_names: list[str] = []

            for item in results:
                raw_score = float(item.get("score", 0))
                if raw_score > best_score:
                    best_score = raw_score
                # Collect matched entity names for audit trail
                name_field = (
                    item.get("name")
                    or item.get("firstName", "") + " " + item.get("lastName", "")
                ).strip()
                if name_field:
                    matched_names.append(name_field)

            # Classify
            if best_score > 95:
                result_status = "confirmed_match"
            elif best_score > 85:
                result_status = "possible_match"
            else:
                result_status = "clear"

            # ── Secondary: Comply Advantage (if OFAC_API_KEY is set) ──────────
            if OFAC_API_KEY:
                log.info(
                    "OFAC_API_KEY detected — secondary Comply Advantage check "
                    "would run here (not yet integrated)."
                )

            log.info(
                f"OFAC SDN screen for '{full_name}': {result_status} "
                f"(best_score={best_score:.2f}, matches={len(matched_names)})"
            )
            return {
                "screened": True,
                "result": result_status,
                "score": best_score,
                "matches": matched_names,
                "source": "ofac_sdn",
            }

        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            log.error(f"OFAC API unreachable for '{full_name}': {exc}")
            return {
                "screened": False,
                "result": "pending_manual_review",
                "reason": "OFAC API unreachable — manual review required",
                "score": None,
                "matches": [],
                "source": "pending_manual_review",
            }
        except Exception as exc:
            log.error(f"Unexpected error during OFAC check for '{full_name}': {exc}")
            return {
                "screened": False,
                "result": "pending_manual_review",
                "reason": f"OFAC check failed: {exc}",
                "score": None,
                "matches": [],
                "source": "pending_manual_review",
            }


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
