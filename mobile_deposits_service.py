"""
Mobile Deposit Service

Handles remote deposit capture workflow:
1. User submits check images (front/back)
2. System analyzes image quality
3. Admin reviews and approves/rejects
4. On approval: creates ledger entry and settles funds
5. Webhooks notify on status changes
"""

from decimal import Decimal
from typing import Dict, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from models import Transaction, Ledger, AuditLog, Account, User, MobileDeposit
from ledger_service import LedgerService
import json
import logging

logger = logging.getLogger(__name__)


class MobileDepositsService:
    """Service for managing mobile deposit workflows."""

    @staticmethod
    async def create_deposit(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        check_number: str,
        issuer_name: str,
        bank_routing: str,
        bank_account: str,
    ) -> Dict:
        """
        Create a new mobile deposit submission.

        Status starts as "pending_images" until images are uploaded.
        """
        try:
            # Verify user exists
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Create deposit record
            deposit = MobileDeposit(
                user_id=user_id,
                amount=amount,
                check_number=check_number,
                issuer_name=issuer_name,
                bank_routing=bank_routing,
                bank_account=bank_account,
                status="pending_images",
                quality_score=None,
                front_image_url=None,
                back_image_url=None,
            )
            db.add(deposit)
            await db.flush()

            logger.info(f"Mobile deposit created for user {user_id}: ${amount}")

            return {
                "success": True,
                "deposit_id": deposit.id,
                "status": deposit.status,
                "amount": float(amount),
                "created_at": deposit.created_at.isoformat() if deposit.created_at else None,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Mobile deposit creation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def add_deposit_image(
        db: AsyncSession,
        deposit_id: int,
        image_side: str,  # "front" or "back"
        image_url: str,
    ) -> Dict:
        """
        Add front or back image to a deposit.

        Once both images present, triggers analysis.
        """
        try:
            deposit = await db.get(MobileDeposit, deposit_id)
            if not deposit:
                return {"success": False, "error": "Deposit not found"}

            if image_side == "front":
                deposit.front_image_url = image_url
            elif image_side == "back":
                deposit.back_image_url = image_url
            else:
                return {"success": False, "error": "Invalid image side (must be 'front' or 'back')"}

            # If both images present, move to pending_analysis
            if deposit.front_image_url and deposit.back_image_url:
                deposit.status = "pending_analysis"

                # Trigger analysis
                analysis_result = await MobileDepositsService.analyze_deposit_images(db, deposit_id)

                db.add(deposit)
                await db.commit()

                return {
                    "success": True,
                    "deposit_id": deposit_id,
                    "status": "pending_analysis",
                    "analysis": analysis_result,
                }

            db.add(deposit)
            await db.commit()

            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": deposit.status,
                "images_uploaded": {
                    "front": deposit.front_image_url is not None,
                    "back": deposit.back_image_url is not None,
                },
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to add deposit image: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def analyze_deposit_images(
        db: AsyncSession,
        deposit_id: int,
    ) -> Dict:
        """
        Analyze deposit check images for quality.

        Mock ML model: random quality score 70-98.
        In production, would call real CV service.
        """
        try:
            deposit = await db.get(MobileDeposit, deposit_id)
            if not deposit:
                return {"success": False, "error": "Deposit not found"}

            # Mock analysis: generate quality score
            import random
            quality_score = random.randint(70, 98)

            deposit.quality_score = quality_score
            deposit.status = "pending_approval"

            db.add(deposit)
            await db.commit()

            logger.info(f"Deposit {deposit_id} analyzed: quality score {quality_score}")

            return {
                "deposit_id": deposit_id,
                "quality_score": quality_score,
                "analysis_passed": quality_score >= 75,
                "details": {
                    "check_detection": "success" if quality_score >= 75 else "failed",
                    "brightness": "optimal",
                    "focus": "sharp" if quality_score >= 85 else "acceptable",
                },
            }

        except Exception as e:
            logger.error(f"Deposit image analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def approve_deposit(
        db: AsyncSession,
        deposit_id: int,
        admin_id: int,
        reviewer_notes: str = "",
    ) -> Dict:
        """
        Admin approves a deposit and settles funds.

        Creates ledger entry, transaction, and settlement.
        """
        try:
            deposit = await db.get(MobileDeposit, deposit_id)
            if not deposit:
                return {"success": False, "error": "Deposit not found"}

            if deposit.status not in ["pending_approval", "rejected"]:
                return {"success": False, "error": f"Cannot approve deposit in status {deposit.status}"}

            # Get user account
            result = await db.execute(
                select(Account)
                .where(Account.owner_id == deposit.user_id)
                .limit(1)
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"success": False, "error": "User account not found"}

            # Create transaction
            transaction = Transaction(
                user_id=deposit.user_id,
                account_id=account.id,
                transaction_type="mobile_deposit",
                amount=deposit.amount,
                direction="credit",
                status="completed",
                description=f"Mobile deposit: check {deposit.check_number}",
                reference_number=f"MD-{deposit.id}-{datetime.utcnow().strftime('%Y%m%d')}",
            )
            db.add(transaction)
            await db.flush()

            # Create double-entry ledger
            ledger_service = LedgerService()
            ledger_result = await ledger_service.create_deposit_entry(
                db=db,
                account_id=account.id,
                amount=deposit.amount,
                reference=f"Mobile deposit {deposit.id}",
                transaction_id=transaction.id,
            )

            if not ledger_result["success"]:
                await db.rollback()
                return ledger_result

            # Update deposit
            deposit.status = "approved"
            deposit.reviewer_id = admin_id
            deposit.review_notes = reviewer_notes

            # Create audit log
            audit = AuditLog(
                admin_id=admin_id,
                user_id=deposit.user_id,
                account_id=account.id,
                action_type="mobile_deposit_approval",
                reason=f"Approved mobile deposit {deposit.id}",
                details=json.dumps({
                    "deposit_id": deposit_id,
                    "amount": float(deposit.amount),
                    "check_number": deposit.check_number,
                    "reviewer_notes": reviewer_notes,
                    "quality_score": deposit.quality_score,
                }),
                status="success",
            )
            db.add(audit)

            db.add(deposit)
            await db.commit()

            logger.info(f"Mobile deposit {deposit_id} approved by admin {admin_id}: ${deposit.amount}")

            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": "approved",
                "amount": float(deposit.amount),
                "transaction_id": transaction.id,
                "settled_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Deposit approval failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def reject_deposit(
        db: AsyncSession,
        deposit_id: int,
        admin_id: int,
        rejection_reason: str,
    ) -> Dict:
        """Admin rejects a deposit."""
        try:
            deposit = await db.get(MobileDeposit, deposit_id)
            if not deposit:
                return {"success": False, "error": "Deposit not found"}

            deposit.status = "rejected"
            deposit.reviewer_id = admin_id
            deposit.review_notes = rejection_reason

            # Create audit log
            audit = AuditLog(
                admin_id=admin_id,
                user_id=deposit.user_id,
                action_type="mobile_deposit_rejection",
                reason=f"Rejected mobile deposit {deposit_id}",
                details=json.dumps({
                    "deposit_id": deposit_id,
                    "amount": float(deposit.amount),
                    "rejection_reason": rejection_reason,
                }),
                status="success",
            )
            db.add(audit)
            db.add(deposit)
            await db.commit()

            logger.info(f"Mobile deposit {deposit_id} rejected by admin {admin_id}")

            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": "rejected",
                "rejection_reason": rejection_reason,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Deposit rejection failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_pending_deposits(db: AsyncSession) -> Dict:
        """Get all pending deposits for admin review."""
        try:
            result = await db.execute(
                select(MobileDeposit)
                .where(MobileDeposit.status.in_(["pending_approval", "pending_images", "pending_analysis"]))
                .order_by(MobileDeposit.created_at.desc())
            )
            deposits = result.scalars().all()

            return {
                "success": True,
                "count": len(deposits),
                "deposits": [
                    {
                        "id": d.id,
                        "user_id": d.user_id,
                        "amount": float(d.amount),
                        "status": d.status,
                        "quality_score": d.quality_score,
                        "check_number": d.check_number,
                        "created_at": d.created_at.isoformat() if d.created_at else None,
                    }
                    for d in deposits
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get pending deposits: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_deposit_stats(db: AsyncSession) -> Dict:
        """Get mobile deposit statistics."""
        try:
            result = await db.execute(select(MobileDeposit))
            all_deposits = result.scalars().all()

            stats = {
                "total_deposits": len(all_deposits),
                "by_status": {},
                "total_amount": 0,
                "average_amount": 0,
            }

            for deposit in all_deposits:
                status = deposit.status
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                stats["total_amount"] += float(deposit.amount)

            if all_deposits:
                stats["average_amount"] = stats["total_amount"] / len(all_deposits)

            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"Failed to get deposit stats: {str(e)}")
            return {"success": False, "error": str(e)}
