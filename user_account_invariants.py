"""
USER-ACCOUNT INVARIANTS ENFORCEMENT

⚠️ CORE RULE (NON-NEGOTIABLE):
Every user must have BOTH a User ID and an Account ID.

This module enforces system invariants and prevents operations that violate core rules.

Invariants:
1️⃣ No transaction without Account ID (❌ No "N/A" or NULL account_id)
2️⃣ No balance without Account ID (must query from account, never from user)
3️⃣ No dashboard data without Account ID
4️⃣ No admin funding without Account ID
5️⃣ User creation = User + Account binding (atomic, one operation)
6️⃣ KYC does NOT create accounts (account exists at registration)
7️⃣ KYC only changes: Account status, limits, permissions
"""

import logging
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User as DBUser, Account as DBAccount, Transaction as DBTransaction
from schemas import User as PydanticUser

log = logging.getLogger(__name__)


class UserAccountInvariantError(Exception):
    """Raised when a core invariant is violated"""
    pass


class InvariantValidator:
    """Enforces system invariants for user-account relationships"""
    
    @staticmethod
    async def ensure_user_has_account(
        db: AsyncSession,
        user_id: int,
        error_prefix: str = "Operation blocked"
    ) -> DBAccount:
        """
        MANDATORY: Verify user has at least one account.
        
        Returns: The primary account (owner_id=user_id)
        Raises: UserAccountInvariantError if user or account missing
        
        Usage:
            account = await InvariantValidator.ensure_user_has_account(db, user_id)
        """
        # Step 1: User must exist
        result = await db.execute(select(DBUser).filter(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise UserAccountInvariantError(
                f"{error_prefix}: User {user_id} does not exist"
            )
        
        # Step 2: User must have account
        result = await db.execute(
            select(DBAccount).filter(DBAccount.owner_id == user_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise UserAccountInvariantError(
                f"{error_prefix}: User {user_id} has no account. "
                f"System invariant violated: every user must have an account. "
                f"User was created without binding to an account."
            )
        
        return account
    
    @staticmethod
    async def validate_transaction_operation(
        db: AsyncSession,
        user_id: int,
        account_id: Optional[int] = None,
        operation: str = "transaction"
    ) -> Tuple[DBUser, DBAccount]:
        """
        MANDATORY for all transaction operations.
        
        Validates that:
        1. User exists
        2. User has account
        3. If account_id provided, it matches user's account
        
        Returns: (user, account)
        Raises: UserAccountInvariantError if any invariant violated
        
        Usage:
            user, account = await InvariantValidator.validate_transaction_operation(
                db, user_id, account_id, "transfer"
            )
        """
        # Ensure user exists with account
        account = await InvariantValidator.ensure_user_has_account(
            db, user_id,
            error_prefix=f"Cannot perform {operation}"
        )
        
        # If account_id specified, verify it matches
        if account_id and account.id != account_id:
            raise UserAccountInvariantError(
                f"Cannot perform {operation}: "
                f"Account {account_id} does not belong to user {user_id}. "
                f"User's account is {account.id}"
            )
        
        result = await db.execute(select(DBUser).filter(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        
        return user, account
    
    @staticmethod
    async def validate_balance_query(
        db: AsyncSession,
        user_id: int
    ) -> Tuple[DBUser, DBAccount, float]:
        """
        MANDATORY for balance queries.
        
        Returns: (user, account, balance)
        Ensures balance calculation is tied to account, not user.
        
        Rule: Balance = sum of completed transactions in account
        Never use stored account.balance for truth - recalculate from transactions
        
        Usage:
            user, account, balance = await InvariantValidator.validate_balance_query(db, user_id)
        """
        user, account = await InvariantValidator.validate_transaction_operation(
            db, user_id, None, "balance query"
        )
        
        # Calculate balance from completed transactions
        result = await db.execute(
            select(DBTransaction).filter(
                (DBTransaction.account_id == account.id) &
                (DBTransaction.status == 'completed')
            )
        )
        transactions = result.scalars().all()
        
        balance = sum(float(t.amount) for t in transactions)
        
        log.info(
            f"✓ Balance query validated for user {user_id}: "
            f"account {account.id}, balance {balance}"
        )
        
        return user, account, balance
    
    @staticmethod
    async def validate_user_kyc_status(
        db: AsyncSession,
        user_id: int
    ) -> Tuple[DBUser, str]:
        """
        Check user's KYC status.
        
        Returns: (user, kyc_status)
        
        KYC States:
        - 'not_started': User registered, no KYC submitted
        - 'pending': KYC submitted, awaiting approval
        - 'approved': KYC approved, can transact
        - 'rejected': KYC rejected, cannot transact
        """
        result = await db.execute(select(DBUser).filter(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserAccountInvariantError(f"User {user_id} not found")
        
        return user, user.kyc_status
    
    @staticmethod
    async def log_invariant_violation(
        user_id: int,
        account_id: Optional[int],
        violation_type: str,
        details: str
    ) -> None:
        """
        Log invariant violations for audit trail.
        
        Usage in error handlers:
            await InvariantValidator.log_invariant_violation(
                user_id=123,
                account_id=None,
                violation_type="missing_account",
                details="User created without account binding"
            )
        """
        log.critical(
            f"🚨 INVARIANT VIOLATION DETECTED 🚨\n"
            f"  Violation Type: {violation_type}\n"
            f"  User ID: {user_id}\n"
            f"  Account ID: {account_id}\n"
            f"  Details: {details}\n"
            f"  Action: Operation blocked, audit recorded"
        )


async def ensure_operation_has_account(
    db: AsyncSession,
    user_id: int,
    operation_name: str = "operation"
) -> DBAccount:
    """
    Shorthand wrapper for InvariantValidator.ensure_user_has_account()
    
    Example usage in routers:
        @router.post("/transfer")
        async def transfer(payload: TransferRequest, db: SessionDep):
            # Ensure user has account before proceeding
            account = await ensure_operation_has_account(db, payload.user_id, "transfer")
            
            # Now safe to use account_id
            await db.execute(
                select(DBTransaction).filter(DBTransaction.account_id == account.id)
            )
    """
    try:
        return await InvariantValidator.ensure_user_has_account(
            db, user_id,
            error_prefix=f"{operation_name} blocked"
        )
    except UserAccountInvariantError as e:
        await InvariantValidator.log_invariant_violation(
            user_id=user_id,
            account_id=None,
            violation_type="missing_account",
            details=str(e)
        )
        raise


async def validate_balance_calculation(
    db: AsyncSession,
    user_id: int
) -> float:
    """
    Get authoritative user balance.
    
    RULE: Balance = sum of all completed transactions for user's account
    NEVER use stored account.balance - always recalculate
    
    Returns: balance (float)
    """
    user, account, balance = await InvariantValidator.validate_balance_query(db, user_id)
    return balance


# Middleware for checking invariants on protected endpoints
async def check_user_account_invariant_middleware(
    user_id: int,
    db: AsyncSession,
    endpoint_name: str = "endpoint"
) -> Dict[str, Any]:
    """
    Use in FastAPI endpoints to ensure invariants before operation.
    
    Example:
        @router.post("/sensitive-operation")
        async def sensitive_op(
            payload: Request,
            db: SessionDep,
            current_user: CurrentUserDep
        ):
            # Check invariants first
            context = await check_user_account_invariant_middleware(
                current_user.id, db, "sensitive_operation"
            )
            
            if not context["valid"]:
                raise HTTPException(status_code=400, detail=context["error"])
            
            # Safe to proceed
            account = context["account"]
            ...
    """
    try:
        account = await InvariantValidator.ensure_user_has_account(
            db, user_id,
            error_prefix=endpoint_name
        )
        return {
            "valid": True,
            "user_id": user_id,
            "account": account,
            "account_id": account.id,
            "error": None
        }
    except UserAccountInvariantError as e:
        return {
            "valid": False,
            "user_id": user_id,
            "account": None,
            "account_id": None,
            "error": str(e)
        }
