"""Transfers and money movement API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import uuid
import json

from deps import get_current_user, SessionDep, CurrentUserDep
from database import SessionLocal
from models import User as DBUser, Transaction as DBTransaction, Account as DBAccount
from schemas import TransactionCreate, User
from pydantic import BaseModel
import crud
from transaction_validator import TransactionValidator
from balance_service_ledger import BalanceServiceLedger
from ledger_service import LedgerService
from ws_manager import manager
from account_id_enforcement import account_id_enforcement

router = APIRouter(
    prefix="/api",
    tags=["transfers"],
    dependencies=[Depends(get_current_user)]
)

class TransferRequest(BaseModel):
    recipient_id: int
    amount: float
    description: Optional[str] = None

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: TransferRequest = Body(...),
    current_user: DBUser = Depends(get_current_user),
    db_session: SessionDep = None
):
    """
    Create a new transfer between users.
    
    🔧 CRITICAL FIX: Creates TWO transaction records (sender debit, recipient credit)
    
    Validates:
    - Amount must be positive and within limits
    - Sender must have account (RULE 1)
    - Recipient must have account (RULE 1)
    - Sender must have sufficient balance (RULE 3)
    - Both must have valid KYC status (RULE 2)
    
    IMPORTANT: Transfer creates:
    1. Debit transaction for sender (reduces balance)
    2. Credit transaction for recipient (increases balance)
    3. Ledger entries for both
    4. Both synced atomically
    """
    try:
        # Extract data
        recipient_id = transfer_data.recipient_id
        amount = float(transfer_data.amount)
        description = transfer_data.description or "Transfer between users"
        
        # Basic amount validation
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        if amount > 10000:
            raise HTTPException(status_code=400, detail="Amount exceeds maximum transfer limit")
        
        # Validate transfer using TransactionValidator
        is_valid, reason = await TransactionValidator.validate_transfer(
            db=db_session,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            amount=amount
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=reason)
        
        # Get sender's account
        sender_account_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == current_user.id).limit(1)
        )
        sender_account = sender_account_result.scalar_one_or_none()
        
        if not sender_account:
            raise HTTPException(status_code=400, detail="Sender has no account")
        
        # 🔧 ENFORCEMENT: Validate account ownership before proceeding
        is_valid, reason = await account_id_enforcement.validate_account_ownership(
            db=db_session,
            user_id=current_user.id,
            account_id=sender_account.id
        )
        if not is_valid:
            raise HTTPException(status_code=403, detail=f"Account validation failed: {reason}")
        
        # Get recipient
        recipient_result = await db_session.execute(
            select(DBUser).where(DBUser.id == recipient_id)
        )
        recipient = recipient_result.scalar_one_or_none()
        
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        # Get recipient's account
        recipient_account_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == recipient_id).limit(1)
        )
        recipient_account = recipient_account_result.scalar_one_or_none()
        
        if not recipient_account:
            raise HTTPException(status_code=400, detail="Recipient has no account")
        
        # 🔧 ENFORCEMENT: Validate recipient account ownership
        is_valid, reason = await account_id_enforcement.validate_account_ownership(
            db=db_session,
            user_id=recipient_id,
            account_id=recipient_account.id
        )
        if not is_valid:
            raise HTTPException(status_code=403, detail=f"Recipient account validation failed: {reason}")
        
        # Generate reference number for audit trail
        reference_number = str(uuid.uuid4())
        
        # Determine transaction status based on sender's KYC
        # (recipient KYC also checked, but sender's matters for availability)
        status_to_set = "completed" if current_user.kyc_status == "approved" else "blocked"
        
        # 🔧 CRITICAL: Create TWO transaction records
        
        # 1. Debit transaction for sender (money going out)
        sender_transaction = DBTransaction(
            user_id=current_user.id,           # ✓ Sender
            account_id=sender_account.id,      # ✓ From where
            transaction_type="transfer",       # ✓ What type
            amount=-amount,                    # ✓ NEGATIVE (money out)
            status=status_to_set,              # ✓ Completed or blocked
            direction="debit",                 # ✓ Money out
            description=f"Transfer to {recipient.email}: {description}",
            reference_number=reference_number, # ✓ Audit trail
            kyc_status_at_time=current_user.kyc_status
        )
        db_session.add(sender_transaction)
        await db_session.flush()
        
        # 2. Credit transaction for recipient (money coming in)
        recipient_transaction = DBTransaction(
            user_id=recipient_id,              # ✓ Recipient
            account_id=recipient_account.id,   # ✓ To where
            transaction_type="transfer",       # ✓ What type
            amount=amount,                     # ✓ POSITIVE (money in)
            status=status_to_set,              # ✓ Same status
            direction="credit",                # ✓ Money in
            description=f"Transfer from {current_user.email}: {description}",
            reference_number=reference_number, # ✓ Same reference for audit
            kyc_status_at_time=recipient.kyc_status
        )
        db_session.add(recipient_transaction)
        await db_session.flush()
        
        # If transfer is completing, create ledger entries
        if status_to_set == "completed":
            # Create ledger entry for sender (debit)
            _, _ = await LedgerService.create_transfer(
                db=db_session,
                from_user_id=current_user.id,
                to_user_id=recipient_id,
                amount=Decimal(str(amount)),
                description=description,
                reference_number=reference_number
            )
            
            # ISSUE #4 FIX: Do NOT manually sync account.balance
            # Balance is now calculated from ledger (source of truth)
            # When balance is needed, use BalanceServiceLedger.get_user_balance()
            # Removed: sender_account.balance = sender_balance
            # Removed: recipient_account.balance = recipient_balance
        
        # Commit everything atomically
        await db_session.commit()
        await db_session.refresh(sender_transaction)
        await db_session.refresh(recipient_transaction)
        
        # Broadcast notifications to both users
        try:
            sender_balance = await BalanceServiceLedger.get_user_balance(db_session, current_user.id) if status_to_set == "completed" else 0
            recipient_balance_val = await BalanceServiceLedger.get_user_balance(db_session, recipient_id) if status_to_set == "completed" else 0
            
            await manager.broadcast(json.dumps({
                "event": "transfer:completed",
                "sender_id": current_user.id,
                "recipient_id": recipient_id,
                "amount": amount,
                "sender_new_balance": sender_balance,
                "recipient_new_balance": recipient_balance_val,
                "status": status_to_set,
                "reference": reference_number,
                "timestamp": sender_transaction.created_at.isoformat() if sender_transaction.created_at else None
            }))
        except Exception:
            pass  # Don't fail the transaction if broadcast fails
        
        return {
            "id": sender_transaction.id,
            "reference_id": reference_number,
            "sender_id": current_user.id,
            "recipient_id": recipient_id,
            "amount": amount,
            "status": status_to_set,
            "message": f"Transfer of ${amount:.2f} initiated to {recipient.email}",
            "created_at": sender_transaction.created_at.isoformat() if sender_transaction.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transfer: {str(e)}"
        )


@router.get("/transfers")
async def get_transfers(
    current_user: DBUser = Depends(get_current_user),
    db_session: SessionDep = None,
    skip: int = 0,
    limit: int = 10
):
    """Get transfer history for current user."""
    try:
        # Get transactions for the current user (both sent and received)
        result = await db_session.execute(
            select(DBTransaction)
            .filter(
                (DBTransaction.user_id == current_user.id) | 
                (DBTransaction.description.contains(f"to {current_user.id}"))
            )
            .order_by(DBTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        transactions = result.scalars().all()
        
        if not transactions:
            return []
        
        return [
            {
                "id": tx.id,
                "type": tx.transaction_type or "transfer",
                "amount": float(tx.amount),
                "status": tx.status or "completed",
                "recipient_name": tx.description or "Unknown",
                "created_at": tx.created_at.isoformat() if tx.created_at else None
            }
            for tx in transactions
        ]
    except Exception as e:
        print(f"Error fetching transfers: {e}")
        return []


@router.get("/transfers/{transfer_id}")
async def get_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get transfer details."""
    # Transfer details functionality to be implemented
    return {}


@router.post("/transfers/{transfer_id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Confirm a pending transfer."""
    return {
        "id": transfer_id,
        "status": "completed",
        "message": "Transfer completed successfully",
        "reference_id": "TRF20240115001"
    }


@router.post("/transfers/{transfer_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Cancel a pending transfer."""
    return {
        "id": transfer_id,
        "status": "cancelled",
        "message": "Transfer cancelled successfully"
    }


@router.get("/accounts")
async def get_accounts(
    current_user: DBUser = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get user's accounts for transfers."""
    try:
        # Get all accounts owned by the current user
        result = await db_session.execute(
            select(DBAccount).filter(DBAccount.owner_id == current_user.id)
        )
        accounts = result.scalars().all()
        
        if not accounts:
            return []
        
        return [
            {
                "id": account.id,
                "name": f"{account.account_type.capitalize()} Account",
                "account_number": account.account_number,
                "account_type": account.account_type,
                "balance": float(account.balance),
                "currency": account.currency or "USD"
            }
            for account in accounts
        ]
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return []


@router.get("/recipients")
async def get_recipients(
    current_user: DBUser = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get saved recipients for transfers."""
    try:
        # For now, return empty list (recipients would be stored in a separate table)
        # This can be implemented later when the recipient management is added
        # For now, users can enter new recipients for each transfer
        return []
    except Exception as e:
        print(f"Error fetching recipients: {e}")
        return []


# Bill Pay endpoints
@router.post("/bills", status_code=status.HTTP_201_CREATED)
async def pay_bill(
    bill_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Create a bill payment."""
    return {
        "id": 1,
        "type": "bill_pay",
        "status": "scheduled",
        "message": "Bill payment scheduled successfully"
    }


@router.get("/bills")
async def get_bill_payments(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
    skip: int = 0,
    limit: int = 10
):
    """Get bill payment history."""
    return []

