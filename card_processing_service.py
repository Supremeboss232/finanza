"""
Card Processing Service

Handles card lifecycle and transactions:
1. Card request and issuance
2. Card activation
3. Transaction authorization
4. Settlement and posting
5. Dispute handling
6. Fraud detection
"""

from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import json
import random
import string
import logging

from models import User, Card, Transaction, Account, Ledger, AuditLog

logger = logging.getLogger(__name__)


class CardProcessingService:
    """Service for managing card lifecycle and transactions."""

    @staticmethod
    def generate_card_number() -> str:
        """Generate a valid Luhn card number (test format)."""
        # Generate random 15 digits
        digits = [random.randint(0, 9) for _ in range(15)]
        
        # Calculate Luhn checksum
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        checksum = (10 - (total % 10)) % 10
        card_number = ''.join(map(str, digits)) + str(checksum)
        
        return card_number

    @staticmethod
    def generate_cvv() -> str:
        """Generate a 3-digit CVV."""
        return str(random.randint(100, 999))

    @staticmethod
    async def request_card(
        db: AsyncSession,
        user_id: int,
        card_type: str,
        billing_address: str,
    ) -> Dict:
        """
        Request a new card.
        
        Card Types: credit, debit, prepaid
        Status: requested → issued → activated → active
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if user.kyc_status != "approved":
                return {"success": False, "error": "KYC approval required"}

            # Create card record
            card = Card(
                user_id=user_id,
                card_number=CardProcessingService.generate_card_number(),
                card_type=card_type,
                card_holder_name=user.full_name,
                expiry_date=(datetime.utcnow() + timedelta(days=365*4)).strftime("%m/%Y"),
                status="requested",
                credit_limit=Decimal("5000") if card_type == "credit" else Decimal("0"),
                balance=Decimal("0"),
            )
            db.add(card)
            await db.commit()

            logger.info(f"Card {card.id} requested for user {user_id}: {card_type}")

            return {
                "success": True,
                "card_id": card.id,
                "card_number": card.card_number[-4:],  # Last 4 digits only
                "card_type": card_type,
                "status": "requested",
                "card_holder_name": user.full_name,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Card request failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def approve_card_request(
        db: AsyncSession,
        card_id: int,
        admin_id: int,
    ) -> Dict:
        """Admin approves card request and issues the card."""
        try:
            card = await db.get(Card, card_id)
            if not card:
                return {"success": False, "error": "Card not found"}

            if card.status != "requested":
                return {"success": False, "error": f"Cannot approve card in status {card.status}"}

            admin = await db.get(User, admin_id)
            if not admin or not admin.is_admin:
                return {"success": False, "error": "Admin verification failed"}

            card.status = "issued"
            db.add(card)

            # Create audit log
            audit = AuditLog(
                admin_id=admin_id,
                user_id=card.user_id,
                action_type="card_approval",
                reason=f"Card approval: {card.card_type}",
                details=json.dumps({
                    "card_id": card_id,
                    "card_number": card.card_number[-4:],
                    "card_type": card.card_type,
                }),
                status="success",
            )
            db.add(audit)
            await db.commit()

            logger.info(f"Card {card_id} approved")

            return {
                "success": True,
                "card_id": card_id,
                "status": "issued",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Card approval failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def activate_card(
        db: AsyncSession,
        card_id: int,
        user_id: int,
    ) -> Dict:
        """User activates their issued card."""
        try:
            card = await db.get(Card, card_id)
            if not card or card.user_id != user_id:
                return {"success": False, "error": "Card not found or unauthorized"}

            if card.status != "issued":
                return {"success": False, "error": f"Cannot activate card in status {card.status}"}

            card.status = "active"
            db.add(card)
            await db.commit()

            logger.info(f"Card {card_id} activated for user {user_id}")

            return {
                "success": True,
                "card_id": card_id,
                "status": "active",
                "card_type": card.card_type,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Card activation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def authorize_transaction(
        db: AsyncSession,
        card_id: int,
        amount: Decimal,
        merchant: str,
        description: str,
    ) -> Dict:
        """
        Authorize a card transaction.
        
        In real processing: check fraud, verify funds, hold amount.
        Here: simulate authorization with basic checks.
        """
        try:
            card = await db.get(Card, card_id)
            if not card:
                return {"success": False, "error": "Card not found"}

            if card.status != "active":
                return {"success": False, "error": "Card is not active"}

            # Fraud check: amount > 2x transaction limit
            if amount > card.transaction_limit * 2:
                return {
                    "success": False,
                    "error": "Transaction exceeds limit",
                    "decline_reason": "amount_exceeds_limit",
                }

            # Credit check: if credit card, verify available credit
            if card.card_type == "credit":
                available_credit = card.credit_limit - card.balance
                if amount > available_credit:
                    return {
                        "success": False,
                        "error": "Insufficient available credit",
                        "decline_reason": "insufficient_credit",
                    }
            else:  # Debit card
                # Verify account funds
                result = await db.execute(
                    select(Account).where(Account.owner_id == card.user_id).limit(1)
                )
                account = result.scalar_one_or_none()
                if not account or account.balance < amount:
                    return {
                        "success": False,
                        "error": "Insufficient funds",
                        "decline_reason": "insufficient_funds",
                    }

            # Authorization approved
            auth_code = f"{random.randint(100000, 999999)}"

            logger.info(f"Card {card_id} authorization: ${amount} at {merchant}")

            return {
                "success": True,
                "card_id": card_id,
                "amount": float(amount),
                "merchant": merchant,
                "auth_code": auth_code,
                "status": "authorized",
            }

        except Exception as e:
            logger.error(f"Card authorization failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def settle_transaction(
        db: AsyncSession,
        card_id: int,
        auth_code: str,
        amount: Decimal,
        merchant: str,
        description: str,
    ) -> Dict:
        """
        Settle an authorized transaction.
        
        Creates transaction and ledger entries.
        """
        try:
            card = await db.get(Card, card_id)
            if not card:
                return {"success": False, "error": "Card not found"}

            # Get user account
            result = await db.execute(
                select(Account).where(Account.owner_id == card.user_id).limit(1)
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"success": False, "error": "User account not found"}

            # Create transaction
            if card.card_type == "credit":
                direction = "credit"
                transaction_type = "card_purchase_credit"
            else:
                direction = "debit"
                transaction_type = "card_purchase_debit"

            transaction = Transaction(
                user_id=card.user_id,
                account_id=account.id,
                transaction_type=transaction_type,
                amount=amount,
                direction=direction,
                status="completed",
                description=f"Card purchase: {merchant}",
                reference_number=auth_code,
            )
            db.add(transaction)
            await db.flush()

            # Create ledger entries
            now = datetime.utcnow()

            if card.card_type == "credit":
                # Credit card: user liability increases
                debit = Ledger(
                    user_id=card.user_id,
                    entry_type="debit",
                    amount=amount,
                    transaction_id=transaction.id,
                    source_user_id=card.user_id,
                    destination_user_id=1,  # Merchant/system
                    description=f"Debit: Card purchase at {merchant}",
                    reference_number=auth_code,
                    status="posted",
                    posted_at=now,
                )
                db.add(debit)
                await db.flush()

                credit = Ledger(
                    user_id=1,
                    entry_type="credit",
                    amount=amount,
                    transaction_id=transaction.id,
                    related_entry_id=debit.id,
                    source_user_id=card.user_id,
                    destination_user_id=1,
                    description=f"Credit: Merchant payment from card",
                    reference_number=auth_code,
                    status="posted",
                    posted_at=now,
                )
                db.add(credit)

                # Update card balance (liability)
                card.balance = card.balance + amount
            else:
                # Debit card: money leaves account
                debit = Ledger(
                    user_id=card.user_id,
                    entry_type="debit",
                    amount=amount,
                    transaction_id=transaction.id,
                    source_user_id=card.user_id,
                    destination_user_id=1,
                    description=f"Debit: Card purchase at {merchant}",
                    reference_number=auth_code,
                    status="posted",
                    posted_at=now,
                )
                db.add(debit)
                await db.flush()

                credit = Ledger(
                    user_id=1,
                    entry_type="credit",
                    amount=amount,
                    transaction_id=transaction.id,
                    related_entry_id=debit.id,
                    source_user_id=card.user_id,
                    destination_user_id=1,
                    description=f"Credit: Merchant payment from debit card",
                    reference_number=auth_code,
                    status="posted",
                    posted_at=now,
                )
                db.add(credit)

                # Update account balance
                account.balance = account.balance - amount

            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)
            db.add(card)
            db.add(account)

            await db.commit()

            logger.info(f"Card {card_id} transaction settled: ${amount}")

            return {
                "success": True,
                "card_id": card_id,
                "amount": float(amount),
                "merchant": merchant,
                "auth_code": auth_code,
                "status": "settled",
                "transaction_id": transaction.id,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Card transaction settlement failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def pay_credit_card_balance(
        db: AsyncSession,
        card_id: int,
        payment_amount: Decimal,
    ) -> Dict:
        """Pay down credit card balance."""
        try:
            card = await db.get(Card, card_id)
            if not card:
                return {"success": False, "error": "Card not found"}

            if card.card_type != "credit":
                return {"success": False, "error": "Only credit cards have balances"}

            if payment_amount > card.balance:
                return {"success": False, "error": "Payment exceeds balance"}

            # Get user account
            result = await db.execute(
                select(Account).where(Account.owner_id == card.user_id).limit(1)
            )
            account = result.scalar_one_or_none()

            if not account or account.balance < payment_amount:
                return {"success": False, "error": "Insufficient account balance"}

            # Create transaction
            transaction = Transaction(
                user_id=card.user_id,
                account_id=account.id,
                transaction_type="credit_card_payment",
                amount=payment_amount,
                direction="debit",
                status="completed",
                description="Credit card payment",
                reference_number=f"CC-PAY-{card_id}",
            )
            db.add(transaction)
            await db.flush()

            # Create ledger entries
            now = datetime.utcnow()

            debit = Ledger(
                user_id=card.user_id,
                entry_type="debit",
                amount=payment_amount,
                transaction_id=transaction.id,
                source_user_id=card.user_id,
                destination_user_id=1,
                description="Debit: Credit card payment",
                reference_number=f"CC-PAY-{card_id}",
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            credit = Ledger(
                user_id=1,
                entry_type="credit",
                amount=payment_amount,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=card.user_id,
                destination_user_id=1,
                description="Credit: Credit card payment received",
                reference_number=f"CC-PAY-{card_id}",
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)

            # Update balances
            card.balance = card.balance - payment_amount
            account.balance = account.balance - payment_amount
            db.add(card)
            db.add(account)

            await db.commit()

            logger.info(f"Credit card {card_id} payment: ${payment_amount}")

            return {
                "success": True,
                "card_id": card_id,
                "payment_amount": float(payment_amount),
                "new_balance": float(card.balance),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Credit card payment failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_card_details(db: AsyncSession, card_id: int, user_id: int) -> Dict:
        """Get card details (user can only see their own cards)."""
        try:
            card = await db.get(Card, card_id)
            if not card or card.user_id != user_id:
                return {"success": False, "error": "Card not found or unauthorized"}

            return {
                "success": True,
                "card_id": card.id,
                "card_number": f"**** **** **** {card.card_number[-4:]}",
                "card_type": card.card_type,
                "card_holder_name": card.card_holder_name,
                "expiry_date": card.expiry_date,
                "status": card.status,
                "balance": float(card.balance),
                "credit_limit": float(card.credit_limit),
                "transaction_limit": float(card.transaction_limit),
            }

        except Exception as e:
            logger.error(f"Failed to get card details: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_user_cards(db: AsyncSession, user_id: int) -> Dict:
        """Get all user's cards."""
        try:
            result = await db.execute(
                select(Card).where(Card.user_id == user_id).order_by(Card.created_at.desc())
            )
            cards = result.scalars().all()

            return {
                "success": True,
                "count": len(cards),
                "cards": [
                    {
                        "card_id": card.id,
                        "card_number": f"**** **** **** {card.card_number[-4:]}",
                        "card_type": card.card_type,
                        "status": card.status,
                        "balance": float(card.balance),
                        "credit_limit": float(card.credit_limit),
                    }
                    for card in cards
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get user cards: {str(e)}")
            return {"success": False, "error": str(e)}
