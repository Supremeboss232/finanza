"""
Payment Processing Service

Handles payment flows (internal bank-to-account):
1. Payment initiation and validation
2. Settlement and routing
3. Reconciliation and confirmation
4. Dispute and chargeback handling
5. Fee calculation and posting
"""

from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import json
import random
import logging

from config import settings
from models import User, Account, Transaction, Ledger, AuditLog
from monitoring_service import AlertService

logger = logging.getLogger(__name__)


class PaymentProcessingService:
    """Service for processing internal bank-to-account payments."""

    # Payment types and their fee structures
    PAYMENT_TYPES = {
        "internal_transfer": {"fee": Decimal("0.00"), "processing_time_hours": 0},
        "ach_debit": {"fee": Decimal("0.50"), "processing_time_hours": 1},
        "ach_credit": {"fee": Decimal("0.50"), "processing_time_hours": 1},
        "wire_transfer": {"fee": Decimal("25.00"), "processing_time_hours": 2},
        "check_payment": {"fee": Decimal("1.00"), "processing_time_hours": 3},
        "bill_pay": {"fee": Decimal("0.00"), "processing_time_hours": 1},
    }

    @staticmethod
    async def initiate_payment(
        db: AsyncSession,
        user_id: int,
        recipient_user_id: int,
        amount: Decimal,
        payment_type: str,
        description: str = "",
    ) -> Dict:
        """
        Initiate a payment from one user to another.
        
        Payment Types: internal_transfer, ach_debit, ach_credit, wire_transfer, check_payment, bill_pay
        """
        try:
            # Verify sender
            sender = await db.get(User, user_id)
            if not sender:
                return {"success": False, "error": "Sender not found"}

            # Verify recipient
            recipient = await db.get(User, recipient_user_id)
            if not recipient:
                return {"success": False, "error": "Recipient not found"}

            if user_id == recipient_user_id:
                return {"success": False, "error": "Cannot pay to self"}

            # Get sender's account
            result = await db.execute(
                select(Account).where(Account.owner_id == user_id).limit(1)
            )
            sender_account = result.scalar_one_or_none()

            if not sender_account:
                return {"success": False, "error": "Sender account not found"}

            # Get recipient's account
            result = await db.execute(
                select(Account).where(Account.owner_id == recipient_user_id).limit(1)
            )
            recipient_account = result.scalar_one_or_none()

            if not recipient_account:
                return {"success": False, "error": "Recipient account not found"}

            # Validate payment type
            if payment_type not in PaymentProcessingService.PAYMENT_TYPES:
                return {"success": False, "error": f"Invalid payment type: {payment_type}"}

            # Get fee
            fee = PaymentProcessingService.PAYMENT_TYPES[payment_type]["fee"]
            total_debit = amount + fee

            # Verify funds
            if sender_account.balance < total_debit:
                return {"success": False, "error": "Insufficient funds"}

            # Create payment transaction
            transaction = Transaction(
                user_id=user_id,
                recipient_user_id=recipient_user_id,
                account_id=sender_account.id,
                transaction_type=payment_type,
                amount=amount,
                direction="debit",
                status="pending",
                description=description or f"Payment to {recipient.full_name}",
                reference_number=f"PAY-{random.randint(100000, 999999)}",
            )
            db.add(transaction)
            await db.flush()
            await db.commit()

            logger.info(f"Payment initiated: ${amount} from user {user_id} to {recipient_user_id}")

            return {
                "success": True,
                "transaction_id": transaction.id,
                "status": "pending",
                "amount": float(amount),
                "fee": float(fee),
                "total_debit": float(total_debit),
                "processing_time_hours": PaymentProcessingService.PAYMENT_TYPES[payment_type]["processing_time_hours"],
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Payment initiation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def settle_payment(
        db: AsyncSession,
        transaction_id: int,
    ) -> Dict:
        """
        Settle a pending payment.
        
        Creates double-entry ledger entries and updates balances.
        """
        try:
            transaction = await db.get(Transaction, transaction_id)
            if not transaction:
                return {"success": False, "error": "Transaction not found"}

            if transaction.status != "pending":
                return {"success": False, "error": f"Cannot settle transaction in status {transaction.status}"}

            # Get sender account
            sender_account = await db.get(Account, transaction.account_id)
            if not sender_account:
                return {"success": False, "error": "Sender account not found"}

            # Get recipient account using stored recipient_user_id
            recipient_account = None
            if transaction.recipient_user_id:
                result = await db.execute(
                    select(Account).where(Account.owner_id == transaction.recipient_user_id).limit(1)
                )
                recipient_account = result.scalar_one_or_none()

            if not recipient_account:
                return {"success": False, "error": "Recipient account not found"}

            # Get fee
            payment_type = transaction.transaction_type
            fee = PaymentProcessingService.PAYMENT_TYPES.get(payment_type, {}).get("fee", Decimal("0"))

            # Create ledger entries
            now = datetime.utcnow()

            # Sender debit (money leaves sender)
            debit = Ledger(
                user_id=transaction.user_id,
                entry_type="debit",
                amount=transaction.amount,
                transaction_id=transaction.id,
                source_user_id=transaction.user_id,
                destination_user_id=recipient_account.owner_id,
                description=f"Debit: Payment settlement",
                reference_number=transaction.reference_number,
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            # Recipient credit (money arrives at recipient)
            credit = Ledger(
                user_id=recipient_account.owner_id,
                entry_type="credit",
                amount=transaction.amount,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=transaction.user_id,
                destination_user_id=recipient_account.owner_id,
                description=f"Credit: Payment received",
                reference_number=transaction.reference_number,
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)

            # Handle fee if applicable
            if fee > 0:
                # Fee debit from sender
                fee_debit = Ledger(
                    user_id=transaction.user_id,
                    entry_type="debit",
                    amount=fee,
                    transaction_id=transaction.id,
                    source_user_id=transaction.user_id,
                    destination_user_id=1,
                    description=f"Debit: Payment fee ({transaction.transaction_type})",
                    reference_number=f"{transaction.reference_number}-FEE",
                    status="posted",
                    posted_at=now,
                )
                db.add(fee_debit)
                await db.flush()

                # Fee credit to system
                fee_credit = Ledger(
                    user_id=1,
                    entry_type="credit",
                    amount=fee,
                    transaction_id=transaction.id,
                    related_entry_id=fee_debit.id,
                    source_user_id=transaction.user_id,
                    destination_user_id=1,
                    description=f"Credit: Payment fee received",
                    reference_number=f"{transaction.reference_number}-FEE",
                    status="posted",
                    posted_at=now,
                )
                db.add(fee_credit)
                await db.flush()

                fee_debit.related_entry_id = fee_credit.id
                db.add(fee_debit)

            # Update transaction status
            transaction.status = "completed"
            db.add(transaction)

            # Update account balances
            sender_account.balance = sender_account.balance - transaction.amount - fee
            recipient_account.balance = recipient_account.balance + transaction.amount
            db.add(sender_account)
            db.add(recipient_account)

            await db.commit()

            logger.info(f"Payment {transaction_id} settled: ${transaction.amount} + ${fee} fee")

            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "completed",
                "amount": float(transaction.amount),
                "fee": float(fee),
                "total_debit": float(transaction.amount + fee),
                "settled_at": now.isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Payment settlement failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def cancel_payment(
        db: AsyncSession,
        transaction_id: int,
    ) -> Dict:
        """Cancel a pending payment."""
        try:
            transaction = await db.get(Transaction, transaction_id)
            if not transaction:
                return {"success": False, "error": "Transaction not found"}

            if transaction.status not in ["pending", "blocked"]:
                return {"success": False, "error": f"Cannot cancel transaction in status {transaction.status}"}

            transaction.status = "cancelled"
            db.add(transaction)
            await db.commit()

            logger.info(f"Payment {transaction_id} cancelled")

            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "cancelled",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Payment cancellation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_payment_status(db: AsyncSession, transaction_id: int) -> Dict:
        """Get payment status and details."""
        try:
            transaction = await db.get(Transaction, transaction_id)
            if not transaction:
                return {"success": False, "error": "Transaction not found"}

            return {
                "success": True,
                "transaction_id": transaction_id,
                "user_id": transaction.user_id,
                "recipient_user_id": transaction.recipient_user_id,
                "amount": float(transaction.amount),
                "transaction_type": transaction.transaction_type,
                "status": transaction.status,
                "description": transaction.description,
                "reference_number": transaction.reference_number,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to get payment status: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_user_payment_history(
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
    ) -> Dict:
        """Get user's payment history."""
        try:
            result = await db.execute(
                select(Transaction)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type.in_(list(PaymentProcessingService.PAYMENT_TYPES.keys()))
                )
                .order_by(Transaction.created_at.desc())
                .limit(limit)
            )
            transactions = result.scalars().all()

            return {
                "success": True,
                "user_id": user_id,
                "count": len(transactions),
                "payments": [
                    {
                        "transaction_id": txn.id,
                        "amount": float(txn.amount),
                        "type": txn.transaction_type,
                        "status": txn.status,
                        "description": txn.description,
                        "reference": txn.reference_number,
                        "created_at": txn.created_at.isoformat() if txn.created_at else None,
                    }
                    for txn in transactions
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get payment history: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def reconcile_payments(db: AsyncSession) -> Dict:
        """
        Reconcile all payments.
        
        Verify that ledger entries balance and flag discrepancies.
        """
        try:
            result = await db.execute(select(Ledger))
            all_entries = result.scalars().all()

            # Calculate totals
            total_credits = sum(e.amount for e in all_entries if e.entry_type == "credit")
            total_debits = sum(e.amount for e in all_entries if e.entry_type == "debit")

            reconciled = total_credits == total_debits
            result = {
                "success": True,
                "reconciled": reconciled,
                "total_credits": float(total_credits),
                "total_debits": float(total_debits),
                "difference": float(abs(total_credits - total_debits)),
                "entry_count": len(all_entries),
            }

            if not reconciled:
                details = (
                    f"Ledger totals mismatch: credits=${total_credits:.2f}, debits=${total_debits:.2f}, "
                    f"difference=${abs(total_credits - total_debits):.2f}."
                )
                logger.warning("Payment reconciliation discrepancy detected: %s", details)
                await AlertService.alert_ledger_discrepancy(
                    summary="Payment reconciliation mismatch",
                    details=details,
                    recipients=[settings.ADMIN_EMAIL]
                )

            return result

        except Exception as e:
            logger.error(f"Reconciliation failed: {str(e)}")
            await AlertService.alert_system_issue(
                summary="Payment reconciliation exception",
                details=str(e),
                recipients=[settings.ADMIN_EMAIL]
            )
            return {"success": False, "error": str(e)}
