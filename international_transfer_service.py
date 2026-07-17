"""
International Transfer and Compliance Service

Handles cross-border transfers with:
- Country risk assessment
- Sanctions screening
- Regulatory compliance checks
- AML/KYC validation
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from models import User, Account, Transaction, AuditLog
import json
import logging

logger = logging.getLogger(__name__)

# High-risk countries (example list - should be updated from external source)
HIGH_RISK_COUNTRIES = ["IR", "SY", "CU", "KP", "SO"]

# Sanctioned individuals/entities (example - integrate with real OFAC list)
SANCTIONED_NAMES = ["osama", "alqaeda"]

# Country tier information
COUNTRY_TIERS = {
    "US": {"tier": "1", "risk_level": "low", "kyc_requirement": "basic"},
    "CA": {"tier": "1", "risk_level": "low", "kyc_requirement": "basic"},
    "GB": {"tier": "1", "risk_level": "low", "kyc_requirement": "basic"},
    "IR": {"tier": "4", "risk_level": "high", "kyc_requirement": "full"},
    "SY": {"tier": "4", "risk_level": "high", "kyc_requirement": "full"},
    "CU": {"tier": "4", "risk_level": "high", "kyc_requirement": "full"},
    "KP": {"tier": "4", "risk_level": "critical", "kyc_requirement": "full"},
}


class InternationalTransferService:
    """Service for managing international transfers with compliance."""

    @staticmethod
    async def assess_country_risk(
        country_code: str,
    ) -> Dict:
        """
        Assess risk level for a country.

        Returns risk assessment with tier, level, and KYC requirements.
        """
        country_code = country_code.upper()

        # Get country info
        country_info = COUNTRY_TIERS.get(country_code, {
            "tier": "3",
            "risk_level": "medium",
            "kyc_requirement": "full"
        })

        return {
            "country_code": country_code,
            "tier": country_info["tier"],
            "risk_level": country_info["risk_level"],
            "kyc_requirement": country_info["kyc_requirement"],
            "is_high_risk": country_code in HIGH_RISK_COUNTRIES,
            "assessment_date": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def screen_sanctions(
        full_name: str,
        country_code: str,
    ) -> Dict:
        """
        Screen a person against sanctions lists.

        Simple keyword matching for demo; production should use real OFAC/etc APIs.
        """
        name_lower = full_name.lower()
        matches = []

        for sanctioned in SANCTIONED_NAMES:
            if sanctioned in name_lower:
                matches.append(sanctioned)

        is_sanctioned = len(matches) > 0

        return {
            "full_name": full_name,
            "country_code": country_code,
            "is_sanctioned": is_sanctioned,
            "matches": matches,
            "risk_level": "critical" if is_sanctioned else "low",
            "screening_date": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def validate_international_transfer(
        db: AsyncSession,
        sender_id: int,
        recipient_country: str,
        amount: Decimal,
        recipient_name: str,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate an international transfer request.

        Checks:
        1. Sender KYC is approved
        2. Country risk assessment
        3. Sanctions screening
        4. AML/CFT rules
        5. Transfer limits

        Returns: (is_valid, reason, compliance_data)
        """
        # Get sender
        sender = await db.get(User, sender_id)
        if not sender:
            return False, "Sender not found", None

        if sender.kyc_status != "approved":
            return False, "Sender must have approved KYC for international transfers", None

        # Assess recipient country
        country_risk = await InternationalTransferService.assess_country_risk(
            recipient_country
        )

        if country_risk["risk_level"] == "critical":
            return False, f"Transfers to {recipient_country} are prohibited", country_risk

        # Screen recipient against sanctions
        sanctions_screen = await InternationalTransferService.screen_sanctions(
            recipient_name,
            recipient_country
        )

        if sanctions_screen["is_sanctioned"]:
            logger.warning(
                f"SANCTIONS ALERT: Attempted transfer to sanctioned entity {recipient_name}"
            )
            return False, "Recipient appears on sanctions list. Transfer blocked.", sanctions_screen

        # Apply transfer limits based on risk level
        limits = {
            "low": Decimal("100000"),
            "medium": Decimal("25000"),
            "high": Decimal("5000"),
        }

        daily_limit = limits.get(country_risk["risk_level"], Decimal("5000"))

        if amount > daily_limit:
            return False, f"Transfer exceeds limit for {recipient_country} (max: ${daily_limit})", country_risk

        # Compile compliance data
        compliance_data = {
            "country_risk": country_risk,
            "sanctions_screen": sanctions_screen,
            "daily_limit": float(daily_limit),
            "compliance_check_time": datetime.utcnow().isoformat(),
        }

        return True, "OK", compliance_data

    @staticmethod
    async def create_international_transfer(
        db: AsyncSession,
        sender_id: int,
        recipient_country: str,
        recipient_name: str,
        recipient_account: str,
        amount: Decimal,
        purpose: str,
        admin_notes: Optional[str] = None,
    ) -> Dict:
        """
        Create an international transfer with compliance documentation.

        Returns transaction and compliance record.
        """
        # Validate the transfer
        is_valid, reason, compliance_data = await InternationalTransferService.validate_international_transfer(
            db=db,
            sender_id=sender_id,
            recipient_country=recipient_country,
            amount=amount,
            recipient_name=recipient_name,
        )

        if not is_valid:
            logger.warning(f"International transfer blocked: {reason}")
            return {
                "success": False,
                "error": reason,
                "compliance_data": compliance_data,
            }

        try:
            # Get sender account
            sender_result = await db.execute(
                select(Account).where(Account.owner_id == sender_id).limit(1)
            )
            sender_account = sender_result.scalar_one_or_none()

            if not sender_account:
                return {"success": False, "error": "Sender has no account"}

            # Create transaction record
            transaction = Transaction(
                user_id=sender_id,
                account_id=sender_account.id,
                transaction_type="international_transfer",
                amount=amount,
                direction="debit",
                status="pending_approval",
                description=f"International transfer to {recipient_country} - {recipient_name}",
                reference_number=f"INTL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{sender_id}",
            )
            db.add(transaction)
            await db.flush()

            # Create audit log with compliance data
            audit_entry = AuditLog(
                admin_id=sender_id,
                user_id=sender_id,
                account_id=sender_account.id,
                action_type="international_transfer",
                reason=purpose,
                details=json.dumps({
                    "recipient_country": recipient_country,
                    "recipient_name": recipient_name,
                    "recipient_account": recipient_account,
                    "amount": float(amount),
                    "compliance_data": compliance_data,
                    "admin_notes": admin_notes,
                }),
                status="success",
            )
            db.add(audit_entry)
            await db.commit()

            logger.info(
                f"International transfer created for user {sender_id}: "
                f"{recipient_country} to {recipient_name} amount {amount}"
            )

            return {
                "success": True,
                "transaction_id": transaction.id,
                "status": "pending_approval",
                "recipient_country": recipient_country,
                "recipient_name": recipient_name,
                "amount": float(amount),
                "compliance_data": compliance_data,
                "audit_log_id": audit_entry.id,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"International transfer creation failed: {str(e)}")
            return {
                "success": False,
                "error": f"Transfer creation failed: {str(e)}",
            }

    @staticmethod
    async def get_international_transfer_rules(
        recipient_country: str,
    ) -> Dict:
        """Get transfer rules and limits for a specific country."""
        country_risk = await InternationalTransferService.assess_country_risk(recipient_country)

        limits = {
            "low": 100000,
            "medium": 25000,
            "high": 5000,
        }

        kyc_requirements = {
            "basic": ["name", "email", "address"],
            "full": ["name", "email", "address", "id_number", "proof_of_address", "occupation"],
        }

        daily_limit = limits.get(country_risk["risk_level"], 5000)
        kyc_required = kyc_requirements.get(
            country_risk["kyc_requirement"],
            kyc_requirements["full"]
        )

        return {
            "country_code": recipient_country,
            "risk_level": country_risk["risk_level"],
            "daily_limit": daily_limit,
            "kyc_requirements": kyc_required,
            "documentation_required": [
                "proof_of_funds",
                "transfer_purpose",
                "recipient_identification",
            ],
            "processing_time_days": 3 if country_risk["risk_level"] == "high" else 1,
            "transfer_fee_percent": 2.5 if country_risk["risk_level"] == "high" else 1.5,
        }
