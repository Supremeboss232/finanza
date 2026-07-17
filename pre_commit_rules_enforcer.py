"""
Pre-Commit Transaction Rule Enforcer

Enforces critical business rules BEFORE any database commit occurs.

This layer ensures transaction safety by validating:
1. KYC status allows transaction completion
2. Accounts exist and are active
3. Balances are sufficient
4. No rejected KYC status for transaction parties

All rule violations are logged for audit trail and compliance.
"""

from decimal import Decimal
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Account
from balance_service_ledger import BalanceServiceLedger
import logging

logger = logging.getLogger(__name__)


class RuleViolationType:
    """Rule violation event types for audit trail"""
    INSUFFICIENT_KYC = "INSUFFICIENT_KYC"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    NO_ACCOUNT = "NO_ACCOUNT"
    INACTIVE_USER = "INACTIVE_USER"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT"
    REJECTED_KYC = "REJECTED_KYC"
    INVALID_AMOUNT = "INVALID_AMOUNT"


class PreCommitRuleEnforcer:
    """
    Enforces all critical transaction rules BEFORE database commit.
    
    This layer is the final guard against invalid transactions:
    - Validates user/account active status
    - Verifies KYC compliance
    - Confirms sufficient balances
    - Logs all violations for audit trail
    """

    @staticmethod
    async def enforce_deposit_pre_commit(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        account_id: int,
        transaction_id: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Enforce rules before committing a deposit transaction.
        
        Returns:
            (allowed: bool, reason: str, violation_type: Optional[str])
        """
        # RULE 1: User must be active
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            violation = RuleViolationType.INACTIVE_USER
            logger.warning(
                f"DEPOSIT BLOCKED - Transaction {transaction_id}: "
                f"User {user_id} is inactive. Violation: {violation}"
            )
            return False, "User account is inactive", violation

        # RULE 2: Account must be active
        account = await db.get(Account, account_id)
        if not account or account.status != "active":
            violation = RuleViolationType.INACTIVE_ACCOUNT
            logger.warning(
                f"DEPOSIT BLOCKED - Transaction {transaction_id}: "
                f"Account {account_id} is inactive. Violation: {violation}"
            )
            return False, "Account is not active", violation

        # RULE 3: KYC cannot be rejected
        if user.kyc_status == "rejected":
            violation = RuleViolationType.REJECTED_KYC
            logger.warning(
                f"DEPOSIT BLOCKED - Transaction {transaction_id}: "
                f"User {user_id} KYC is rejected. Violation: {violation}"
            )
            return False, "User KYC has been rejected", violation

        logger.info(
            f"DEPOSIT APPROVED - Transaction {transaction_id}: "
            f"Pre-commit rules passed. User: {user_id}, Amount: {amount}"
        )
        return True, "All pre-commit rules passed", None

    @staticmethod
    async def enforce_transfer_pre_commit(
        db: AsyncSession,
        sender_id: int,
        recipient_id: int,
        amount: Decimal,
        transaction_id: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Enforce rules before committing a transfer transaction.
        
        Rules checked:
        - Both parties active
        - Both have accounts
        - Both accounts active
        - Sender has sufficient balance
        - Neither party has rejected KYC
        
        Returns:
            (allowed: bool, reason: str, violation_type: Optional[str])
        """
        # RULE 1: Both parties must be active
        sender = await db.get(User, sender_id)
        if not sender or not sender.is_active:
            violation = RuleViolationType.INACTIVE_USER
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Sender {sender_id} is inactive. Violation: {violation}"
            )
            return False, "Sender account is inactive", violation

        recipient = await db.get(User, recipient_id)
        if not recipient or not recipient.is_active:
            violation = RuleViolationType.INACTIVE_USER
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Recipient {recipient_id} is inactive. Violation: {violation}"
            )
            return False, "Recipient account is inactive", violation

        # RULE 2: Both must have accounts
        sender_result = await db.execute(
            select(Account).where(Account.user_id == sender_id).limit(1)
        )
        sender_account = sender_result.scalar_one_or_none()
        if not sender_account:
            violation = RuleViolationType.NO_ACCOUNT
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Sender {sender_id} has no account. Violation: {violation}"
            )
            return False, "Sender has no account", violation

        recipient_result = await db.execute(
            select(Account).where(Account.user_id == recipient_id).limit(1)
        )
        recipient_account = recipient_result.scalar_one_or_none()
        if not recipient_account:
            violation = RuleViolationType.NO_ACCOUNT
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Recipient {recipient_id} has no account. Violation: {violation}"
            )
            return False, "Recipient has no account", violation

        # RULE 3: Both accounts must be active
        if sender_account.status != "active":
            violation = RuleViolationType.INACTIVE_ACCOUNT
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Sender account {sender_account.id} is inactive. Violation: {violation}"
            )
            return False, "Sender account is not active", violation

        if recipient_account.status != "active":
            violation = RuleViolationType.INACTIVE_ACCOUNT
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Recipient account {recipient_account.id} is inactive. Violation: {violation}"
            )
            return False, "Recipient account is not active", violation

        # RULE 4: Sender must have sufficient balance
        sender_balance = await BalanceServiceLedger.get_user_balance(db, sender_id)
        if sender_balance < amount:
            violation = RuleViolationType.INSUFFICIENT_BALANCE
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Sender {sender_id} insufficient balance. Have: {sender_balance}, Need: {amount}. "
                f"Violation: {violation}"
            )
            return False, f"Insufficient balance. Have: {sender_balance}, Need: {amount}", violation

        # RULE 5: Neither party can have rejected KYC
        if sender.kyc_status == "rejected":
            violation = RuleViolationType.REJECTED_KYC
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Sender {sender_id} KYC is rejected. Violation: {violation}"
            )
            return False, "Sender KYC has been rejected", violation

        if recipient.kyc_status == "rejected":
            violation = RuleViolationType.REJECTED_KYC
            logger.warning(
                f"TRANSFER BLOCKED - Transaction {transaction_id}: "
                f"Recipient {recipient_id} KYC is rejected. Violation: {violation}"
            )
            return False, "Recipient KYC has been rejected", violation

        logger.info(
            f"TRANSFER APPROVED - Transaction {transaction_id}: "
            f"Pre-commit rules passed. Sender: {sender_id}, Recipient: {recipient_id}, Amount: {amount}"
        )
        return True, "All pre-commit rules passed", None

    @staticmethod
    async def enforce_withdrawal_pre_commit(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        account_id: int,
        transaction_id: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Enforce rules before committing a withdrawal transaction.
        
        Rules checked:
        - User is active
        - Account is active
        - User has sufficient balance
        - KYC is not rejected
        
        Returns:
            (allowed: bool, reason: str, violation_type: Optional[str])
        """
        # RULE 1: User must be active
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            violation = RuleViolationType.INACTIVE_USER
            logger.warning(
                f"WITHDRAWAL BLOCKED - Transaction {transaction_id}: "
                f"User {user_id} is inactive. Violation: {violation}"
            )
            return False, "User account is inactive", violation

        # RULE 2: Account must be active
        account = await db.get(Account, account_id)
        if not account or account.status != "active":
            violation = RuleViolationType.INACTIVE_ACCOUNT
            logger.warning(
                f"WITHDRAWAL BLOCKED - Transaction {transaction_id}: "
                f"Account {account_id} is inactive. Violation: {violation}"
            )
            return False, "Account is not active", violation

        # RULE 3: Sufficient balance required
        balance = await BalanceServiceLedger.get_user_balance(db, user_id)
        if balance < amount:
            violation = RuleViolationType.INSUFFICIENT_BALANCE
            logger.warning(
                f"WITHDRAWAL BLOCKED - Transaction {transaction_id}: "
                f"User {user_id} insufficient balance. Have: {balance}, Need: {amount}. "
                f"Violation: {violation}"
            )
            return False, f"Insufficient balance. Have: {balance}, Need: {amount}", violation

        # RULE 4: KYC cannot be rejected
        if user.kyc_status == "rejected":
            violation = RuleViolationType.REJECTED_KYC
            logger.warning(
                f"WITHDRAWAL BLOCKED - Transaction {transaction_id}: "
                f"User {user_id} KYC is rejected. Violation: {violation}"
            )
            return False, "User KYC has been rejected", violation

        logger.info(
            f"WITHDRAWAL APPROVED - Transaction {transaction_id}: "
            f"Pre-commit rules passed. User: {user_id}, Amount: {amount}"
        )
        return True, "All pre-commit rules passed", None
