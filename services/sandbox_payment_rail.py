"""Local sandbox payment rail for development and QA.

This gives the app a deterministic, offline payment path for deposits and
simulated settlement without depending on real payment providers.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ledger_service import LedgerService
from models import Account, Transaction

logger = logging.getLogger(__name__)


class SandboxPaymentRailService:
    """Simple in-app payment rail for sandbox testing."""

    @staticmethod
    async def create_sandbox_deposit(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        description: str = "Sandbox deposit",
        reference_number: Optional[str] = None,
    ) -> Dict[str, object]:
        """Create a mock deposit transaction and ledger entries."""
        try:
            if amount <= 0:
                return {"success": False, "error": "Amount must be positive"}

            account_result = await db.execute(select(Account).where(Account.owner_id == user_id).limit(1))
            account = account_result.scalar_one_or_none()
            if not account:
                return {"success": False, "error": "No account found for user"}

            transaction = Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=amount,
                transaction_type="deposit",
                direction="credit",
                status="completed",
                description=description,
                reference_number=reference_number,
                kyc_status_at_time="approved",
            )
            db.add(transaction)
            await db.flush()

            await LedgerService.create_deposit(
                db=db,
                user_id=user_id,
                amount=amount,
                description=description,
                transaction_id=transaction.id,
                reference_number=reference_number,
            )
            await db.commit()

            logger.info("Sandbox deposit completed for user %s: %s", user_id, amount)
            return {
                "success": True,
                "transaction_id": transaction.id,
                "amount": float(amount),
                "status": "completed",
            }
        except Exception as exc:
            await db.rollback()
            logger.exception("Sandbox deposit failed: %s", exc)
            return {"success": False, "error": str(exc)}

    @staticmethod
    async def simulate_settlement(db: AsyncSession, transaction_id: int, status: str = "completed") -> Dict[str, object]:
        """Mark a sandbox transaction as settled or failed for QA flows."""
        try:
            tx = await db.get(Transaction, transaction_id)
            if not tx:
                return {"success": False, "error": "Transaction not found"}

            tx.status = status
            db.add(tx)
            await db.commit()
            return {"success": True, "transaction_id": tx.id, "status": status}
        except Exception as exc:
            await db.rollback()
            logger.exception("Sandbox settlement update failed: %s", exc)
            return {"success": False, "error": str(exc)}
