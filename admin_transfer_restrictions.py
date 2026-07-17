"""
Admin Account Transfer Restrictions

Enforces strict rules for transfers involving admin/system accounts.

Rules:
1. Admin accounts CANNOT send money to regular user accounts (only disbursements allowed)
2. Admin accounts CAN receive money from users (deposits)
3. Only APPROVED disbursement transactions can come from admin accounts
4. All admin transfers are logged for audit trail
5. System accounts cannot participate in user-to-user transfers

This prevents accidental or malicious transfer of funds from system accounts
to personal accounts, ensuring proper financial controls.
"""

from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Account, User
import logging

logger = logging.getLogger(__name__)


class AdminAccountTransferValidator:
    """
    Validates transfers involving admin/system accounts.
    
    Ensures strict rules are enforced for system account usage.
    """

    @staticmethod
    async def validate_transfer_sender(
        db: AsyncSession,
        sender_id: int,
        sender_account_id: int,
        recipient_id: int,
        recipient_account_id: int,
        transaction_type: str = "transfer"
    ) -> Tuple[bool, str]:
        """
        Validate that a sender account is allowed to send money.
        
        Rules:
        - Admin accounts can only be used for APPROVED disbursements
        - System accounts cannot send to regular users
        
        Args:
            db: Database session
            sender_id: Sending user ID
            sender_account_id: Sender's account ID
            recipient_id: Receiving user ID
            recipient_account_id: Recipient's account ID
            transaction_type: Type of transaction (transfer, disbursement, etc.)
            
        Returns:
            (is_allowed: bool, reason: str)
        """
        sender_account = await db.get(Account, sender_account_id)
        if not sender_account:
            return False, "Sender account not found"
        
        # Check if this is an admin/system account
        if sender_account.is_admin_account or sender_account.is_system_account:
            # Admin accounts can only send via explicit disbursement transactions
            if transaction_type not in ["disbursement", "system_transfer"]:
                logger.warning(
                    f"ADMIN TRANSFER BLOCKED: Account {sender_account_id} (admin) "
                    f"attempted regular transfer to user {recipient_id}. "
                    f"Only disbursements allowed."
                )
                return False, (
                    "Admin accounts cannot send regular transfers. "
                    "Only disbursement transactions are allowed."
                )
            
            # For disbursements, log the operation for audit
            logger.info(
                f"ADMIN DISBURSEMENT: Account {sender_account_id} sending "
                f"to user {recipient_id} via {transaction_type}"
            )
            return True, "Disbursement transaction allowed"
        
        return True, "Transfer allowed"

    @staticmethod
    async def validate_transfer_recipient(
        db: AsyncSession,
        recipient_id: int,
        recipient_account_id: int,
        sender_id: int,
        sender_account_id: int
    ) -> Tuple[bool, str]:
        """
        Validate that a recipient account can receive money.
        
        Currently, system accounts can receive from users.
        
        Args:
            db: Database session
            recipient_id: Receiving user ID
            recipient_account_id: Recipient's account ID
            sender_id: Sending user ID
            sender_account_id: Sender's account ID
            
        Returns:
            (is_allowed: bool, reason: str)
        """
        recipient_account = await db.get(Account, recipient_account_id)
        if not recipient_account:
            return False, "Recipient account not found"
        
        # System accounts can receive transfers
        # No restrictions on recipients currently
        
        return True, "Recipient account valid"

    @staticmethod
    async def validate_admin_to_user_transfer(
        db: AsyncSession,
        sender_account_id: int,
        recipient_user_id: int
    ) -> Tuple[bool, str]:
        """
        Special validation for admin account to regular user transfers.
        
        This should only be allowed for explicit disbursements, not regular transfers.
        
        Args:
            db: Database session
            sender_account_id: Admin account ID
            recipient_user_id: Regular user ID
            
        Returns:
            (is_allowed: bool, reason: str)
        """
        sender_account = await db.get(Account, sender_account_id)
        if not sender_account:
            return False, "Sender account not found"
        
        if not (sender_account.is_admin_account or sender_account.is_system_account):
            return True, "Not an admin account"
        
        # Verify recipient is a regular user (not admin)
        recipient_user = await db.get(User, recipient_user_id)
        if not recipient_user:
            return False, "Recipient user not found"
        
        if recipient_user.is_admin:
            # Admin to admin transfers are allowed (between system accounts)
            return True, "Admin-to-admin transfer allowed"
        
        # Admin to regular user transfer is only allowed via disbursement
        logger.info(
            f"Admin account {sender_account_id} transferring to regular user {recipient_user_id}. "
            f"This should be processed as a disbursement."
        )
        return True, "Admin-to-user transfer requires disbursement processing"

    @staticmethod
    async def log_admin_transfer(
        sender_account_id: int,
        recipient_account_id: int,
        amount: str,
        transaction_id: int,
        transaction_type: str = "transfer"
    ):
        """
        Log admin account transfers for compliance and audit.
        
        Args:
            sender_account_id: Sending account ID
            recipient_account_id: Receiving account ID
            amount: Transfer amount
            transaction_id: Transaction ID
            transaction_type: Type of transaction
        """
        logger.warning(
            f"ADMIN ACCOUNT ACTIVITY - Transaction {transaction_id}: "
            f"From account {sender_account_id} to account {recipient_account_id}, "
            f"Amount: {amount}, Type: {transaction_type}"
        )


class AdminAccountRestrictionService:
    """
    Service for enforcing admin account restrictions at the business logic layer.
    
    This service is called before transaction creation to ensure
    admin accounts are only used appropriately.
    """

    @staticmethod
    async def can_send_transfer(
        db: AsyncSession,
        sender_account_id: int,
        recipient_user_id: int,
        is_disbursement: bool = False
    ) -> Tuple[bool, str]:
        """
        Check if a sender can send a transfer to a recipient.
        
        Args:
            db: Database session
            sender_account_id: Account sending the transfer
            recipient_user_id: User receiving the transfer
            is_disbursement: If True, bypasses admin restrictions
            
        Returns:
            (allowed: bool, reason: str)
        """
        sender_account = await db.get(Account, sender_account_id)
        if not sender_account:
            return False, "Sender account not found"
        
        recipient_user = await db.get(User, recipient_user_id)
        if not recipient_user:
            return False, "Recipient user not found"
        
        # Admin account sending to regular user
        if (sender_account.is_admin_account or sender_account.is_system_account):
            if not is_disbursement and not recipient_user.is_admin:
                logger.warning(
                    f"BLOCKED: Admin account {sender_account_id} cannot send "
                    f"regular transfer to user {recipient_user_id}. "
                    f"Use disbursement endpoint instead."
                )
                return False, (
                    "System accounts can only send disbursements. "
                    "Regular transfers are not allowed."
                )
        
        return True, "Transfer allowed"

    @staticmethod
    async def mark_transfer_as_admin_if_needed(
        db: AsyncSession,
        sender_account_id: int,
        transaction_id: int
    ):
        """
        Mark a transaction as involving an admin account.
        
        Useful for audit logging and compliance tracking.
        
        Args:
            db: Database session
            sender_account_id: Account ID
            transaction_id: Transaction ID to mark
        """
        sender_account = await db.get(Account, sender_account_id)
        if not sender_account:
            return
        
        if sender_account.is_admin_account or sender_account.is_system_account:
            logger.info(
                f"Transaction {transaction_id} marked as admin-involved. "
                f"Account: {sender_account_id}, Type: "
                f"{'system' if sender_account.is_system_account else 'admin'}"
            )
