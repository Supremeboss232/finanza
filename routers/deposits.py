from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated
import uuid
import json

from deps import CurrentUserDep, SessionDep
from schemas import Deposit as PydanticDeposit, DepositCreate, TransactionCreate
from crud import get_user_deposits, create_user_deposit, get_deposit, create_user_transaction
from transaction_validator import TransactionValidator
from transaction_gate_ledger import TransactionGate
from models import Account as DBAccount, User as DBUser, Transaction as DBTransaction
from balance_service_ledger import BalanceServiceLedger
from ledger_service import LedgerService
from ws_manager import manager
from decimal import Decimal

deposits_router = APIRouter(prefix="/deposits", tags=["deposits"])

@deposits_router.post("/", response_model=PydanticDeposit, status_code=status.HTTP_201_CREATED)
async def create_deposit_for_current_user(
    deposit: DepositCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    """
    Create a deposit for the current user.
    
    🔧 CRITICAL FIX: Creates a Transaction record (not just Deposit)
    This ensures the balance system can see the deposit.
    
    RULE 1: No account, no money → User must have account
    RULE 2: No KYC approval → Transaction blocked, doesn't affect balance
    RULE 3: Balance derived → From ledger entries, not stored
    
    Flow:
    1. Validate user, amount, account
    2. Create Transaction record (source of truth for balance)
    3. Create ledger entries (double-entry accounting)
    4. Mark transaction completed (if KYC approved)
    5. Sync account.balance from ledger
    6. Return deposit data
    """
    try:
        # Validate the deposit request
        is_valid, reason = await TransactionValidator.validate_deposit(
            db=db_session,
            user_id=current_user.id,
            amount=deposit.amount,
            account_id=getattr(deposit, 'account_id', None)
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason
            )
        
        # Get user's primary account (must exist due to validation)
        account_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == current_user.id).limit(1)
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no account"
            )
        
        # Get user for KYC status
        user_result = await db_session.execute(
            select(DBUser).where(DBUser.id == current_user.id)
        )
        user = user_result.scalar_one_or_none()
        
        # 🔧 CRITICAL: Create Transaction record (not just Deposit)
        # This is what the balance system queries!
        amount = float(deposit.amount)
        reference_number = str(uuid.uuid4())
        
        # Determine status based on KYC
        status_to_set = "completed" if user.kyc_status == "approved" else "blocked"
        
        transaction = DBTransaction(
            user_id=current_user.id,  # ✓ REQUIRED: Track who made it
            account_id=account.id,    # ✓ REQUIRED: Track where it goes
            transaction_type="deposit",  # ✓ REQUIRED: What type
            amount=amount,            # ✓ REQUIRED: How much
            status=status_to_set,     # ✓ REQUIRED: Is it valid?
            direction="credit",       # ✓ Money coming in
            description=f"User deposit",
            reference_number=reference_number,  # ✓ REQUIRED: Audit trail
            kyc_status_at_time=user.kyc_status  # Snapshot for compliance
        )
        db_session.add(transaction)
        await db_session.flush()
        
        # If deposit is completing, create ledger entries
        if status_to_set == "completed":
            # Create double-entry ledger entries
            debit_entry, credit_entry = await LedgerService.create_admin_funding(
                db=db_session,
                transaction=transaction,
                to_user_id=current_user.id,
                amount=Decimal(str(amount)),
                description=f"User deposit",
                reference_number=reference_number
            )
            
            # Sync account.balance from ledger (source of truth)
            new_balance = await BalanceServiceLedger.get_user_balance(db_session, current_user.id)
            account.balance = new_balance
            db_session.add(account)
        
        # Create Deposit record for UI reference (historical record)
        db_deposit = await create_user_deposit(db=db_session, deposit=deposit, user_id=current_user.id)
        
        # Commit everything atomically
        await db_session.commit()
        await db_session.refresh(transaction)
        
        # Broadcast real-time notification
        try:
            balance = await BalanceServiceLedger.get_user_balance(db_session, current_user.id) if status_to_set == "completed" else 0
            await manager.broadcast(json.dumps({
                "event": "deposit:created",
                "user_id": current_user.id,
                "amount": amount,
                "new_balance": balance,
                "status": status_to_set,
                "reference": reference_number,
                "timestamp": transaction.created_at.isoformat() if transaction.created_at else None
            }))
        except Exception:
            pass  # Don't fail the transaction if broadcast fails
        
        return db_deposit
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deposit: {str(e)}"
        )

@deposits_router.get("/", response_model=List[PydanticDeposit])
async def read_deposits_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_deposits(db=db_session, user_id=current_user.id, skip=skip, limit=limit)

@deposits_router.get("/{deposit_id}", response_model=PydanticDeposit)
async def read_deposit_by_id(
    deposit_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_deposit = await get_deposit(db_session, deposit_id)
    if db_deposit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit not found")
    if db_deposit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this deposit")
    return db_deposit
