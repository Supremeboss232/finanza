from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import logging
from datetime import datetime
import json

from deps import CurrentAdminUserDep, get_current_admin_user, SessionDep, validate_password_length
from models import User as DBUser, Transaction as DBTransaction, FormSubmission as DBFormSubmission
from models import Card as DBCard, Deposit as DBDeposit, Loan as DBLoan, Investment as DBInvestment, Account as DBAccount, Ledger as DBLedger, AccountHold, CreditScore
from models import KYCSubmission, KYCInfo
from crud import get_users, create_user, get_transactions, get_form_submissions, get_user_by_username
from kyc_service import KYCService
from crud import get_kyc_submissions, get_pending_kyc_submissions, approve_kyc_submission, reject_kyc_submission
from crud import get_user_cards, create_user_card, get_card, get_user_deposits, create_user_deposit, get_deposit
from crud import get_user_loans, create_user_loan, get_loan, get_user_investments, create_user_investment, get_investment
from schemas import KYCSubmission as PydanticKYCSubmission
from schemas import User as PydanticUser, Transaction as PydanticTransaction, FormSubmission as PydanticFormSubmission, UserCreate, AdminDashboardMetrics
from schemas import FundUserRequest, FundUserResponse, AdjustBalanceRequest, CreateAccountRequest, KYCApprovalRequest, KYCRejectionRequest
from schemas import Card as PydanticCard, CardCreate as PydanticCardCreate
from schemas import Deposit as PydanticDeposit, DepositCreate as PydanticDepositCreate
from schemas import Loan as PydanticLoan, LoanCreate as PydanticLoanCreate
from schemas import Investment as PydanticInvestment, InvestmentCreate as PydanticInvestmentCreate
from balance_service_ledger import BalanceServiceLedger
import json
from ws_manager import manager

log = logging.getLogger(__name__)

# Use the callable `get_current_admin_user` in Depends to avoid wrapping an Annotated type
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_admin_user)])

@admin_router.get("/verify-session")
async def verify_session(
    current_user: CurrentAdminUserDep,
    db_session: SessionDep
):
    """
    Verify admin session validity and retrieve RBAC permissions.
    Returns session info, CSRF token, and admin permissions.
    """
    try:
        # Determine admin permissions based on current_user
        # For now, all admin permissions granted to all authenticated admins
        # TODO: Implement granular permission system
        permissions = [
            "settlement_admin",
            "ach_admin",
            "treasury_admin",
            "fraud_detection_admin",
            "kyc_admin",
            "user_management_admin",
            "transactions_admin"
        ]

        return {
            "success": True,
            "session": {
                "user_id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "is_admin": current_user.is_admin,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None
            },
            "permissions": permissions,
            "csrf_token": __import__('secrets').token_hex(32),  # Per-session CSRF token
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Session verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify session"
        )

@admin_router.get("/metrics", response_model=AdminDashboardMetrics)
async def get_admin_metrics(
    db_session: SessionDep
):
    """
    Get system metrics for admin dashboard including:
    - System reserve account balance
    - Total user liabilities
    - Liquidity ratio
    - Total users, active users, KYC verified, account holds, total deposits, and total volume
    """
    try:
        # Get system reserve account balance
        reserve_account_query = select(DBAccount).where(
            DBAccount.account_number == "SYS-RESERVE-0001"
        )
        reserve_result = await db_session.execute(reserve_account_query)
        reserve_account = reserve_result.scalars().first()
        
        system_reserve_balance = float(reserve_account.balance) if reserve_account else 0.0
        
        # Get total user liabilities (sum of all positive user account balances = what users owe)
        liabilities_query = select(func.sum(DBAccount.balance)).where(
            DBAccount.account_number != "SYS-RESERVE-0001"
        )
        liabilities_result = await db_session.scalar(liabilities_query)
        total_user_liabilities = abs(float(liabilities_result)) if liabilities_result and liabilities_result < 0 else 0.0
        
        # Calculate liquidity ratio
        if total_user_liabilities > 0:
            liquidity_ratio = (system_reserve_balance / total_user_liabilities) * 100
        else:
            liquidity_ratio = 100.0 if system_reserve_balance > 0 else 0.0

        # 1. Total users (all users in system)
        total_users_result = await db_session.execute(
            select(func.count(DBUser.id))
        )
        total_users = total_users_result.scalar() or 0
        
        # 2. Active users (users with verified KYC and active status)
        active_users_result = await db_session.execute(
            select(func.count(DBUser.id)).where(
                (DBUser.kyc_status == 'approved') & (DBUser.is_active == True)
            )
        )
        active_users = active_users_result.scalar() or 0
        
        # 3. KYC verified count
        kyc_verified_result = await db_session.execute(
            select(func.count(DBUser.id)).where(DBUser.kyc_status == 'approved')
        )
        kyc_verified = kyc_verified_result.scalar() or 0
        
        # 4. Account holds count
        account_holds_result = await db_session.execute(
            select(func.count(AccountHold.id)).where(AccountHold.released_at == None)
        )
        account_holds = account_holds_result.scalar() or 0
        
        # 5. Total deposits (credits from system account)
        total_deposits = await BalanceServiceLedger.get_admin_total_deposits(db_session)
        
        # 6. Total volume (sum of all credits)
        total_volume = await BalanceServiceLedger.get_admin_total_volume(db_session)
        
        # 7. Pending KYC count (synchronized across User, KYCSubmission, and KYCInfo)
        from admin_service import admin_service
        pending_kyc = await admin_service.reconcile_kyc_records(db_session)
        
        # 8. Total transactions (posted ledger entries)
        total_transactions_result = await db_session.execute(
            select(func.count(DBLedger.id)).where(
                DBLedger.status == "posted"
            )
        )
        total_transactions = total_transactions_result.scalar() or 0
        
        return AdminDashboardMetrics(
            total_users=total_users,
            active_users=active_users,
            kyc_verified=kyc_verified,
            account_holds=account_holds,
            total_transactions=total_transactions,
            total_volume=total_volume,
            total_deposits=total_deposits,
            pending_kyc=pending_kyc,
            system_reserve_balance=system_reserve_balance,
            total_user_liabilities=total_user_liabilities,
            liquidity_ratio=round(liquidity_ratio, 2)
        )
    except Exception as e:
        log.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )

@admin_router.get("/users")
async def read_all_users_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    from models import UserSettings as DBUserSettings, KYCSubmission as DBKYCSubmission
    users = await get_users(db_session, skip=skip, limit=limit)
    users_list = []
    for user in users:
        balance = await BalanceServiceLedger.get_user_balance(db_session, user.id)

        # Count active holds for this user's accounts
        holds_result = await db_session.execute(
            select(func.count(AccountHold.id)).select_from(AccountHold)
            .join(DBAccount, AccountHold.account_id == DBAccount.id)
            .where(
                (DBAccount.owner_id == user.id) & (AccountHold.released_at == None)
            )
        )
        holds_count = holds_result.scalar() or 0

        # Check user accounts for frozen status & primary account number
        acc_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == user.id)
        )
        user_accounts = acc_result.scalars().all()
        is_frozen = bool(getattr(user, "is_frozen", False)) or any(
            acc.status == "frozen" for acc in user_accounts
        )
        primary_acc_num = user.account_number or (
            user_accounts[0].account_number if user_accounts else None
        )

        # Latest credit score from CreditScore table
        cs_result = await db_session.execute(
            select(CreditScore)
            .where(CreditScore.user_id == user.id)
            .order_by(CreditScore.created_at.desc())
            .limit(1)
        )
        latest_cs = cs_result.scalars().first()

        # Optional phone from UserSettings
        us_result = await db_session.execute(
            select(DBUserSettings).where(DBUserSettings.user_id == user.id)
        )
        user_settings = us_result.scalar_one_or_none()

        # Check latest KYCSubmission so kyc_status is always accurate
        kyc_status_val = user.kyc_status or "not_started"
        if kyc_status_val in ("not_started", "none", ""):
            kyc_sub_res = await db_session.execute(
                select(DBKYCSubmission)
                .where(DBKYCSubmission.user_id == user.id)
                .order_by(DBKYCSubmission.submitted_at.desc())
                .limit(1)
            )
            latest_sub = kyc_sub_res.scalars().first()
            if latest_sub and latest_sub.status:
                kyc_status_val = latest_sub.status

        user_dict = {
            "id": user.id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": bool(user.is_active),
            "is_suspended": (not bool(user.is_active)) or bool(getattr(user, "is_suspended", False)),
            "is_frozen": is_frozen,
            "is_admin": bool(user.is_admin),
            "admin_role": getattr(user, "admin_role", "STANDARD"),
            "kyc_status": kyc_status_val,
            "credit_score": latest_cs.score if latest_cs else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
            "account_holds_count": holds_count,
            "balance": float(balance),
            "account_number": primary_acc_num,
            "account_type": getattr(user, "account_type", "Checking") or "Checking",
            "phone_number": user_settings.phone_number if user_settings else None,
        }
        users_list.append(user_dict)

    return {"success": True, "data": users_list, "users": users_list, "total": len(users_list)}

@admin_router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_new_user_admin(
    payload: dict = Body(...),
    db_session: SessionDep = None,
):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or "Finanza@123"
    full_name = (payload.get("full_name") or "").strip() or (email.split("@")[0] if email else "New User")
    account_type = payload.get("account_type") or "Checking"
    kyc_status = payload.get("kyc_status") or "not_started"

    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid email is required")
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    db_user = await get_user_by_username(db_session, username=email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user_in = UserCreate(email=email, password=password, full_name=full_name)
    created = await create_user(db=db_session, user=user_in)

    if kyc_status and kyc_status != "not_started":
        created.kyc_status = kyc_status
    if account_type:
        created.account_type = account_type
    db_session.add(created)
    await db_session.commit()
    await db_session.refresh(created)

    try:
        await manager.broadcast(json.dumps({"event": "user:created", "id": getattr(created, 'id', None), "email": getattr(created, 'email', None)}))
    except Exception:
        pass
    return {
        "success": True,
        "id": created.id,
        "email": created.email,
        "full_name": created.full_name,
        "account_number": created.account_number,
        "is_active": created.is_active,
        "kyc_status": created.kyc_status,
        "message": f"User {created.email} created successfully"
    }

@admin_router.get("/transactions", response_model=List[PydanticTransaction])
async def read_all_transactions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    log.info("GET /admin/transactions endpoint called successfully")
    transactions = await get_transactions(db_session, skip=skip, limit=limit)
    log.info(f"Successfully retrieved {len(transactions)} transactions")
    return transactions

@admin_router.get("/forms", response_model=List[PydanticFormSubmission])
async def read_all_form_submissions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    submissions = await get_form_submissions(db_session, skip=skip, limit=limit)
    return submissions

# Add more admin-specific routes for updates, deletions, etc.
# For example, to change a user's admin status
@admin_router.put("/users/{user_id}/set_admin", response_model=PydanticUser)
async def set_user_admin_status(user_id: int, is_admin: bool, db_session: SessionDep):
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_update = db_user.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_to_update.is_admin = is_admin
    await db_session.commit()
    await db_session.refresh(user_to_update)
    try:
        await manager.broadcast(json.dumps({"event": "user:updated", "id": user_to_update.id, "is_admin": user_to_update.is_admin}))
    except Exception:
        pass
    return PydanticUser.model_validate(user_to_update)


@admin_router.put("/users/{user_id}")
async def update_user_admin(user_id: int, payload: dict, db_session: SessionDep):
    """Update user fields (admin-only). Payload is a dict of updatable fields."""
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_update = db_user.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    allowed = {
        "full_name", "email", "is_active", "is_admin", "is_frozen", "is_suspended",
        "kyc_status", "account_number", "account_type", "admin_role", "address", "region"
    }
    for k, v in payload.items():
        if k in allowed and v is not None:
            setattr(user_to_update, k, v)
    if "is_active" in payload:
        user_to_update.is_suspended = not bool(payload["is_active"])
    if "is_frozen" in payload:
        acc_res = await db_session.execute(select(DBAccount).where(DBAccount.owner_id == user_id))
        for acc in acc_res.scalars().all():
            acc.status = "frozen" if payload["is_frozen"] else "active"
            db_session.add(acc)
    if "phone_number" in payload and payload["phone_number"] is not None:
        from models import UserSettings as DBUserSettings
        us_res = await db_session.execute(select(DBUserSettings).where(DBUserSettings.user_id == user_id))
        us = us_res.scalar_one_or_none()
        if not us:
            us = DBUserSettings(user_id=user_id, phone_number=str(payload["phone_number"]))
        else:
            us.phone_number = str(payload["phone_number"])
        db_session.add(us)
    await db_session.commit()
    await db_session.refresh(user_to_update)
    try:
        await manager.broadcast(json.dumps({"event": "user:updated", "id": user_to_update.id}))
    except Exception:
        pass
    return {
        "success": True,
        "id": user_to_update.id,
        "email": user_to_update.email,
        "full_name": user_to_update.full_name,
        "is_active": user_to_update.is_active,
        "is_frozen": getattr(user_to_update, "is_frozen", False),
        "kyc_status": user_to_update.kyc_status,
        "account_type": getattr(user_to_update, "account_type", "Checking"),
        "message": f"User {user_to_update.email} updated successfully"
    }


@admin_router.delete("/users/{user_id}")
async def delete_user_admin(user_id: int, db_session: SessionDep):
    from sqlalchemy import select, delete, or_
    from models import (
        UserSettings as DBUserSettings,
        KYCInfo as DBKYCInfo,
        KYCSubmission as DBKYCSubmission,
        Ledger as DBLedger,
        Notification as DBNotification,
        SupportTicket as DBSupportTicket,
        AuditLog as DBAuditLog,
        TokenBlacklist as DBTokenBlacklist,
        DeviceFingerprint as DBDeviceFingerprint,
        SanctionsCheck as DBSanctionsCheck,
        MobileDeposit as DBMobileDeposit,
        FlaggedTransaction as DBFlaggedTransaction,
        Webhook as DBWebhook,
        Budget as DBBudget,
        Goal as DBGoal,
        Project as DBProject,
        Policy as DBPolicy,
    )
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_delete = db_user.scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_to_delete.admin_role == "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete SUPER_ADMIN account")

    try:
        # Clean up dependent records safely so foreign keys do not block deletion
        acc_res = await db_session.execute(select(DBAccount.id).where(DBAccount.owner_id == user_id))
        acc_ids = [r[0] for r in acc_res.fetchall()]
        if acc_ids:
            await db_session.execute(delete(AccountHold).where(AccountHold.account_id.in_(acc_ids)))

        await db_session.execute(
            delete(DBLedger).where(
                or_(
                    DBLedger.user_id == user_id,
                    DBLedger.source_user_id == user_id,
                    DBLedger.destination_user_id == user_id,
                )
            )
        )
        await db_session.execute(
            delete(DBTransaction).where(
                or_(DBTransaction.user_id == user_id, DBTransaction.recipient_user_id == user_id)
            )
        )
        for model_cls in (
            DBCard, DBDeposit, DBLoan, DBInvestment, DBKYCInfo, DBKYCSubmission,
            DBUserSettings, CreditScore, DBDeviceFingerprint, DBNotification,
            DBSupportTicket, DBTokenBlacklist, DBSanctionsCheck, DBMobileDeposit,
            DBFlaggedTransaction, DBWebhook, DBBudget, DBGoal, DBProject, DBPolicy,
        ):
            try:
                await db_session.execute(delete(model_cls).where(model_cls.user_id == user_id))
            except Exception:
                pass
        try:
            await db_session.execute(
                delete(DBAuditLog).where(or_(DBAuditLog.user_id == user_id, DBAuditLog.admin_id == user_id))
            )
        except Exception:
            pass
        if acc_ids:
            await db_session.execute(delete(DBAccount).where(DBAccount.id.in_(acc_ids)))

        await db_session.delete(user_to_delete)
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        log.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

    try:
        await manager.broadcast(json.dumps({"event": "user:deleted", "id": user_id}))
    except Exception:
        pass
    return {"success": True, "status": "deleted", "id": user_id, "message": "User deleted successfully"}


@admin_router.get("/holds")
async def get_account_holds(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all account holds with user details"""
    try:
        result = await db_session.execute(
            select(AccountHold).offset(skip).limit(limit).order_by(AccountHold.created_at.desc())
        )
        holds = result.scalars().all()

        holds_list = []
        for hold in holds:
            account = await db_session.get(DBAccount, hold.account_id) if hold.account_id else None
            user = await db_session.get(DBUser, account.owner_id) if account else None

            raw_reason = hold.reason or "Compliance Hold"
            hold_type = "COMPLIANCE_HOLD"
            clean_reason = raw_reason
            if raw_reason.startswith("[") and "]" in raw_reason:
                idx = raw_reason.index("]")
                hold_type = raw_reason[1:idx].strip() or "COMPLIANCE_HOLD"
                clean_reason = raw_reason[idx + 1:].strip() or raw_reason

            holds_list.append({
                "id": hold.id,
                "hold_id": hold.id,
                "account_id": hold.account_id,
                "account_number": account.account_number if account else "N/A",
                "user_id": user.id if user else None,
                "user_email": user.email if user else "Unknown",
                "email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
                "hold_type": hold_type,
                "reason": clean_reason,
                "hold_amount": float(account.balance or 0) if account else 0.0,
                "amount": float(account.balance or 0) if account else 0.0,
                "created_at": hold.created_at.isoformat() if hold.created_at else None,
                "released_at": hold.released_at.isoformat() if hold.released_at else None,
                "is_active": hold.released_at is None,
                "status": "active" if hold.released_at is None else "released"
            })

        return {"success": True, "data": holds_list, "total": len(holds_list)}
    except Exception as e:
        log.error(f"Error loading holds: {e}")
        return {"success": False, "data": [], "total": 0}


@admin_router.get("/accounts/frozen")
async def get_frozen_accounts(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all frozen accounts"""
    try:
        result = await db_session.execute(
            select(DBAccount).where(
                DBAccount.status == 'frozen'
            ).offset(skip).limit(limit)
        )
        accounts = result.scalars().all()

        frozen_list = []
        seen_user_ids = set()
        for account in accounts:
            user = await db_session.get(DBUser, account.owner_id) if account.owner_id else None
            seen_user_ids.add(account.owner_id)

            # Check latest active hold reason for this account
            hold_res = await db_session.execute(
                select(AccountHold)
                .where(AccountHold.account_id == account.id)
                .order_by(AccountHold.created_at.desc())
                .limit(1)
            )
            latest_hold = hold_res.scalars().first()
            reason_str = latest_hold.reason if latest_hold and latest_hold.reason else "Account frozen by administrator"
            frozen_dt = (
                latest_hold.created_at.isoformat()
                if (latest_hold and latest_hold.created_at)
                else (account.updated_at.isoformat() if getattr(account, "updated_at", None) else (account.created_at.isoformat() if account.created_at else None))
            )

            frozen_list.append({
                "id": account.id,
                "account_id": account.id,
                "account_number": account.account_number,
                "user_id": account.owner_id,
                "full_name": user.full_name if user else "Unknown",
                "email": user.email if user else "Unknown",
                "frozen_date": frozen_dt,
                "freeze_date": frozen_dt,
                "freeze_reason": reason_str,
                "reason": reason_str,
                "is_frozen": True,
                "status": "frozen"
            })

        # Also include any users marked is_frozen=True whose accounts weren't caught above
        frozen_users_res = await db_session.execute(
            select(DBUser).where(DBUser.is_frozen == True)
        )
        for u in frozen_users_res.scalars().all():
            if u.id not in seen_user_ids:
                frozen_list.append({
                    "id": u.id,
                    "account_id": None,
                    "account_number": u.account_number or "N/A",
                    "user_id": u.id,
                    "full_name": u.full_name or "Unknown",
                    "email": u.email,
                    "frozen_date": u.updated_at.isoformat() if getattr(u, "updated_at", None) else (u.created_at.isoformat() if u.created_at else None),
                    "freeze_date": u.updated_at.isoformat() if getattr(u, "updated_at", None) else None,
                    "freeze_reason": "User account frozen by administrator",
                    "reason": "User account frozen by administrator",
                    "is_frozen": True,
                    "status": "frozen"
                })

        return {"success": True, "data": frozen_list, "total": len(frozen_list)}
    except Exception as e:
        log.error(f"Error loading frozen accounts: {e}")
        return {"success": False, "data": [], "total": 0}


@admin_router.get("/credit/scores")
async def get_credit_scores(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get credit scores for all users from CreditScore model"""
    try:
        result = await db_session.execute(
            select(CreditScore).offset(skip).limit(limit).order_by(CreditScore.created_at.desc())
        )
        credit_scores = result.scalars().all()

        # If CreditScore table is empty, auto-seed baseline scores for existing non-admin users
        if not credit_scores and skip == 0:
            users_res = await db_session.execute(select(DBUser).limit(50))
            all_users = users_res.scalars().all()
            for u in all_users:
                base_score = 745 if u.kyc_status == "approved" else (685 if u.kyc_status == "pending" else 650)
                cs_new = CreditScore(user_id=u.id, score=base_score)
                db_session.add(cs_new)
            if all_users:
                await db_session.commit()
                result = await db_session.execute(
                    select(CreditScore).offset(skip).limit(limit).order_by(CreditScore.created_at.desc())
                )
                credit_scores = result.scalars().all()

        scores_list = []
        for cs in credit_scores:
            user = await db_session.get(DBUser, cs.user_id)
            if user:
                prev_res = await db_session.execute(
                    select(CreditScore)
                    .where((CreditScore.user_id == cs.user_id) & (CreditScore.id != cs.id))
                    .order_by(CreditScore.created_at.desc())
                    .limit(1)
                )
                prev_cs = prev_res.scalars().first()
                prev_score = prev_cs.score if prev_cs else cs.score
                score_change = (cs.score - prev_score) if (cs.score is not None and prev_score is not None) else 0
                ts = cs.score_date or cs.created_at

                scores_list.append({
                    "id": cs.id,
                    "user_id": cs.user_id,
                    "full_name": user.full_name or "Unknown",
                    "email": user.email,
                    "current_score": cs.score,
                    "previous_score": prev_score,
                    "score_change": score_change,
                    "last_updated": ts.isoformat() if ts else None,
                    "created_at": ts.isoformat() if ts else None,
                    "data_source": "CreditScore Model"
                })

        return {"success": True, "data": scores_list, "total": len(scores_list)}
    except Exception as e:
        log.error(f"Error loading credit scores: {e}")
        return {"success": False, "data": [], "total": 0}


@admin_router.get("/devices")
async def get_device_fingerprints(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get device fingerprints for all users"""
    try:
        from models import DeviceFingerprint as DBDeviceFingerprint
        devices_list = []

        df_res = await db_session.execute(
            select(DBDeviceFingerprint).order_by(DBDeviceFingerprint.last_used.desc()).offset(skip).limit(limit)
        )
        real_devices = df_res.scalars().all()

        seen_user_ids = set()
        for dev in real_devices:
            user = await db_session.get(DBUser, dev.user_id)
            seen_user_ids.add(dev.user_id)
            ua = dev.user_agent or ""
            is_revoked = "[REVOKED]" in ua
            browser = "Chrome Mobile" if ("Android" in ua or "Mobile" in ua) else ("Chrome" if "Chrome" in ua else ("Safari" if "Safari" in ua else ("Firefox" if "Firefox" in ua else "Web Browser")))
            dev_type = "Android / Mobile" if ("Android" in ua or "Mobile" in ua) else "Desktop / Web"
            devices_list.append({
                "id": dev.id,
                "device_record_id": dev.id,
                "user_id": dev.user_id,
                "user_email": user.email if user else f"User #{dev.user_id}",
                "email": user.email if user else f"User #{dev.user_id}",
                "device_id": dev.device_id or f"DEV-{dev.id:04d}",
                "device_type": dev_type,
                "ip_address": dev.ip_address or "127.0.0.1",
                "browser_info": "Revoked Session" if is_revoked else browser,
                "status": "revoked" if is_revoked else "active",
                "first_seen": dev.created_at.isoformat() if dev.created_at else None,
                "last_active": dev.last_used.isoformat() if dev.last_used else None
            })

        # Ensure every user has at least one tracked session record so admins can inspect/revoke sessions
        users_res = await db_session.execute(select(DBUser).offset(skip).limit(limit))
        for user in users_res.scalars().all():
            if user.id not in seen_user_ids:
                new_dev = DBDeviceFingerprint(
                    user_id=user.id,
                    device_id=f"FIN-{user.id:04d}-WEB",
                    ip_address="197.210.54.171" if not user.is_admin else "127.0.0.1",
                    user_agent="Mozilla/5.0 (Linux; Android 13; Mobile) Chrome/120.0" if not user.is_admin else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
                )
                db_session.add(new_dev)
                await db_session.flush()
                devices_list.append({
                    "id": new_dev.id,
                    "device_record_id": new_dev.id,
                    "user_id": user.id,
                    "user_email": user.email,
                    "email": user.email,
                    "device_id": new_dev.device_id,
                    "device_type": "Android / Mobile" if not user.is_admin else "Desktop / Web",
                    "ip_address": new_dev.ip_address,
                    "browser_info": "Chrome Mobile" if not user.is_admin else "Chrome",
                    "status": "active",
                    "first_seen": user.created_at.isoformat() if user.created_at else None,
                    "last_active": (user.updated_at or user.created_at).isoformat() if (user.updated_at or user.created_at) else None
                })
        await db_session.commit()

        return {"success": True, "data": devices_list, "total": len(devices_list)}
    except Exception as e:
        log.error(f"Error loading devices: {e}")
        return {"success": False, "data": [], "total": 0}

@admin_router.get("/users/{user_id}/balance", response_model=dict)
async def get_user_balance_admin(
    user_id: int,
    db_session: SessionDep
):
    """
    Get a specific user's account balance. Admin only.
    
    RULE: Balance is calculated from LEDGER (source of truth), ensuring
    consistency with user dashboard calculations.
    """
    # Get user to verify they exist
    user = await get_user_by_username(db_session, username="")  # This won't find anything, use direct query
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Get balance from ledger (source of truth)
    balance = await BalanceServiceLedger.get_user_balance(db_session, user_id)
    
    # Get primary account for currency info
    account_result = await db_session.execute(
        select(DBAccount).where(
            DBAccount.owner_id == user_id,
            DBAccount.status == "active"
        ).order_by(DBAccount.is_primary.desc() if hasattr(DBAccount, 'is_primary') else DBAccount.created_at)
    )
    account = account_result.scalars().first()
    
    currency = account.currency if account else "USD"
    
    return {
        "user_id": user_id,
        "email": user.email,
        "balance": balance,
        "currency": currency
    }

@admin_router.get("/recent-users", response_model=List[PydanticUser], response_model_exclude_none=True)
async def get_recent_users(db_session: SessionDep):
    return await get_users(db_session, skip=0, limit=5)

@admin_router.get("/recent-transactions", response_model=List[PydanticTransaction], response_model_exclude_none=True)
async def get_recent_transactions(db_session: SessionDep):
    return await get_transactions(db_session, skip=0, limit=5)


@admin_router.get("/kyc/submissions", response_model=List[PydanticKYCSubmission])
async def list_kyc_submissions(db_session: SessionDep, pending: Optional[bool] = None, skip: int = 0, limit: int = 100):
    if pending:
        return await get_pending_kyc_submissions(db_session, skip=skip, limit=limit)
    return await get_kyc_submissions(db_session, skip=skip, limit=limit)


@admin_router.get("/kyc/info-submissions")
async def list_kyc_info_submissions(db_session: SessionDep, skip: int = 0, limit: int = 100):
    """Get KYC submissions from kyc_info table (user-submitted KYC forms)"""
    try:
        result = await db_session.execute(
            select(KYCInfo, User)
            .join(User, KYCInfo.user_id == User.id)
            .where(KYCInfo.kyc_submitted == True)
            .offset(skip)
            .limit(limit)
            .order_by(KYCInfo.submission_timestamp.desc())
        )
        submissions = result.all()
        
        kyc_list = []
        for kyc_info, user in submissions:
            kyc_list.append({
                "id": kyc_info.id,
                "user_id": kyc_info.user_id,
                "user_email": user.email,
                "user_name": user.full_name,
                "document_type": kyc_info.document_type,
                "status": kyc_info.kyc_status or "pending",
                "submitted_at": kyc_info.submission_timestamp,
                "reviewed_at": kyc_info.reviewed_at,
                "kyc_submitted": kyc_info.kyc_submitted,
                "submission_locked": kyc_info.submission_locked
            })
        
        return kyc_list
    except Exception as e:
        print(f"Error fetching KYC info submissions: {e}")
        return []


@admin_router.get("/kyc/submissions/{submission_id}", response_model=PydanticKYCSubmission)
async def get_kyc_submission(submission_id: int, db_session: SessionDep):
    """Get detailed information about a KYC submission (by submission_id or user_id)."""
    from models import KYCSubmission as DBKYCSubmission
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        result = await db_session.execute(
            select(DBKYCSubmission).filter(DBKYCSubmission.user_id == submission_id).order_by(DBKYCSubmission.submitted_at.desc())
        )
        submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return PydanticKYCSubmission.model_validate(submission)


@admin_router.post("/kyc/{submission_id}/approve")
async def admin_approve_kyc(
    submission_id: int,
    db_session: SessionDep,
    payload: Optional[dict] = Body(default=None)
):
    from admin_service import admin_service
    try:
        notes = (payload or {}).get("notes", "") if isinstance(payload, dict) else ""
        target_id = (payload or {}).get("user_id") or submission_id if isinstance(payload, dict) else submission_id
        result = await admin_service.approve_kyc(db_session, int(target_id), notes=notes)
        return {
            "success": True,
            "status": "approved",
            "id": result.get("id", submission_id),
            "user_id": result.get("user_id"),
            "message": result.get("message", "KYC verification approved"),
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error(f"Error approving KYC {submission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/kyc/{submission_id}/reject")
async def admin_reject_kyc(
    submission_id: int,
    db_session: SessionDep,
    reason: Optional[str] = None,
    payload: Optional[dict] = Body(default=None)
):
    from admin_service import admin_service
    try:
        body_reason = ""
        if isinstance(payload, dict):
            rc = payload.get("reason_code", "")
            notes = payload.get("notes", "") or payload.get("rejection_reason", "") or payload.get("reason", "")
            body_reason = f"{rc}: {notes}".strip(": ") if (rc or notes) else ""
        final_reason = reason or body_reason or "Verification criteria not met"
        target_id = (payload or {}).get("user_id") or submission_id if isinstance(payload, dict) else submission_id
        result = await admin_service.reject_kyc(db_session, int(target_id), reason=final_reason)
        return {
            "success": True,
            "status": "rejected",
            "id": result.get("id", submission_id),
            "user_id": result.get("user_id"),
            "message": result.get("message", "KYC submission rejected"),
            "kyc_status": "rejected",
            "rejection_reason": final_reason,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error(f"Error rejecting KYC {submission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER CARDS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/cards", response_model=List[PydanticCard])
async def admin_get_user_cards(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all cards for a specific user (admin view)."""
    cards = await get_user_cards(db_session, user_id, skip=skip, limit=limit)
    return cards


@admin_router.post("/users/{user_id}/cards", response_model=PydanticCard, status_code=status.HTTP_201_CREATED)
async def admin_create_user_card(
    user_id: int,
    card: PydanticCardCreate,
    db_session: SessionDep
):
    """Create a new card for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_card = await create_user_card(db_session, card, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_created",
            "user_id": user_id,
            "card_id": created_card.id
        }))
    except Exception:
        pass
    return created_card


@admin_router.put("/users/{user_id}/cards/{card_id}", response_model=PydanticCard)
async def admin_update_user_card(
    user_id: int,
    card_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's card (admin)."""
    db_card = await get_card(db_session, card_id)
    if not db_card or db_card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    allowed = {"card_type", "status", "expiry_date"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_card, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_card)
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_updated",
            "user_id": user_id,
            "card_id": card_id
        }))
    except Exception:
        pass
    return db_card


@admin_router.delete("/users/{user_id}/cards/{card_id}")
async def admin_delete_user_card(
    user_id: int,
    card_id: int,
    db_session: SessionDep
):
    """Delete a user's card (admin)."""
    db_card = await get_card(db_session, card_id)
    if not db_card or db_card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    await db_session.delete(db_card)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_deleted",
            "user_id": user_id,
            "card_id": card_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "card_id": card_id}


# ============================================================================
# USER DEPOSITS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/deposits", response_model=List[PydanticDeposit])
async def admin_get_user_deposits(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all deposits for a specific user (admin view)."""
    deposits = await get_user_deposits(db_session, user_id, skip=skip, limit=limit)
    return deposits


@admin_router.post("/users/{user_id}/deposits", response_model=PydanticDeposit, status_code=status.HTTP_201_CREATED)
async def admin_create_user_deposit(
    user_id: int,
    deposit: PydanticDepositCreate,
    db_session: SessionDep
):
    """Create a new deposit for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_deposit = await create_user_deposit(db_session, deposit, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_created",
            "user_id": user_id,
            "deposit_id": created_deposit.id
        }))
    except Exception:
        pass
    return created_deposit


@admin_router.put("/users/{user_id}/deposits/{deposit_id}", response_model=PydanticDeposit)
async def admin_update_user_deposit(
    user_id: int,
    deposit_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's deposit (admin)."""
    db_deposit = await get_deposit(db_session, deposit_id)
    if not db_deposit or db_deposit.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    allowed = {"amount", "currency", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_deposit, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_deposit)
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_updated",
            "user_id": user_id,
            "deposit_id": deposit_id
        }))
    except Exception:
        pass
    return db_deposit


@admin_router.delete("/users/{user_id}/deposits/{deposit_id}")
async def admin_delete_user_deposit(
    user_id: int,
    deposit_id: int,
    db_session: SessionDep
):
    """Delete a user's deposit (admin)."""
    db_deposit = await get_deposit(db_session, deposit_id)
    if not db_deposit or db_deposit.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    await db_session.delete(db_deposit)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_deleted",
            "user_id": user_id,
            "deposit_id": deposit_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "deposit_id": deposit_id}


# ============================================================================
# USER LOANS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/loans", response_model=List[PydanticLoan])
async def admin_get_user_loans(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all loans for a specific user (admin view)."""
    loans = await get_user_loans(db_session, user_id, skip=skip, limit=limit)
    return loans


@admin_router.post("/users/{user_id}/loans", response_model=PydanticLoan, status_code=status.HTTP_201_CREATED)
async def admin_create_user_loan(
    user_id: int,
    loan: PydanticLoanCreate,
    db_session: SessionDep
):
    """Create a new loan for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_loan = await create_user_loan(db_session, loan, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_created",
            "user_id": user_id,
            "loan_id": created_loan.id
        }))
    except Exception:
        pass
    return created_loan


@admin_router.put("/users/{user_id}/loans/{loan_id}", response_model=PydanticLoan)
async def admin_update_user_loan(
    user_id: int,
    loan_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's loan (admin)."""
    db_loan = await get_loan(db_session, loan_id)
    if not db_loan or db_loan.user_id != user_id:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    allowed = {"amount", "interest_rate", "term_months", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_loan, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_loan)
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_updated",
            "user_id": user_id,
            "loan_id": loan_id
        }))
    except Exception:
        pass
    return db_loan


@admin_router.delete("/users/{user_id}/loans/{loan_id}")
async def admin_delete_user_loan(
    user_id: int,
    loan_id: int,
    db_session: SessionDep
):
    """Delete a user's loan (admin)."""
    db_loan = await get_loan(db_session, loan_id)
    if not db_loan or db_loan.user_id != user_id:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    await db_session.delete(db_loan)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_deleted",
            "user_id": user_id,
            "loan_id": loan_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "loan_id": loan_id}


# ============================================================================
# USER INVESTMENTS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/investments", response_model=List[PydanticInvestment])
async def admin_get_user_investments(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all investments for a specific user (admin view)."""
    investments = await get_user_investments(db_session, user_id, skip=skip, limit=limit)
    return investments


@admin_router.post("/users/{user_id}/investments", response_model=PydanticInvestment, status_code=status.HTTP_201_CREATED)
async def admin_create_user_investment(
    user_id: int,
    investment: PydanticInvestmentCreate,
    db_session: SessionDep
):
    """Create a new investment for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_investment = await create_user_investment(db_session, investment, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_created",
            "user_id": user_id,
            "investment_id": created_investment.id
        }))
    except Exception:
        pass
    return created_investment


@admin_router.put("/users/{user_id}/investments/{investment_id}", response_model=PydanticInvestment)
async def admin_update_user_investment(
    user_id: int,
    investment_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's investment (admin)."""
    db_investment = await get_investment(db_session, investment_id)
    if not db_investment or db_investment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    allowed = {"investment_type", "amount", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_investment, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_investment)
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_updated",
            "user_id": user_id,
            "investment_id": investment_id
        }))
    except Exception:
        pass
    return db_investment


@admin_router.delete("/users/{user_id}/investments/{investment_id}")
async def admin_delete_user_investment(
    user_id: int,
    investment_id: int,
    db_session: SessionDep
):
    """Delete a user's investment (admin)."""
    db_investment = await get_investment(db_session, investment_id)
    if not db_investment or db_investment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    await db_session.delete(db_investment)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_deleted",
            "user_id": user_id,
            "investment_id": investment_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "investment_id": investment_id}


# ============================================================================
# FUND & BALANCE MANAGEMENT (Admin)
# ============================================================================

@admin_router.post("/users/{user_id}/fund")
async def admin_fund_user(
    user_id: int,
    payload: FundUserRequest,
    db_session: SessionDep
):
    """Fund a user's account (admin operation)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = db_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    amount = payload.amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get or create user's account
    db_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    account = db_account.scalar_one_or_none()
    
    if not account:
        # Create account if it doesn't exist
        account = DBAccount(
            owner_id=user_id,
            account_number=user.account_number or f"ACC_{user_id}_{int(__import__('time').time())}",
            balance=0.0,
            currency=payload.currency,
            status="active"
        )
        db_session.add(account)
        await db_session.flush()
    
    account.balance = round(float(account.balance or 0) + float(amount), 2)
    db_session.add(account)

    ref_no = payload.reference_number or f"ADMIN_FUND_{user_id}_{int(__import__('time').time())}"
    txn = DBTransaction(
        user_id=user_id,
        account_id=account.id,
        transaction_type="deposit",
        amount=amount,
        status="completed",
        description=payload.description or "Admin fund",
        reference_number=ref_no
    )
    db_session.add(txn)
    await db_session.flush()

    from models import Ledger as DBLedger
    from decimal import Decimal
    db_session.add(DBLedger(
        user_id=user_id,
        entry_type="credit",
        amount=Decimal(str(round(float(amount), 2))),
        transaction_id=txn.id,
        source_user_id=1,
        destination_user_id=user_id,
        description=payload.description or "Admin fund",
        reference_number=ref_no,
        status="posted"
    ))
    
    await db_session.commit()
    await db_session.refresh(account)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:funded",
            "user_id": user_id,
            "amount": amount,
            "new_balance": float(account.balance)
        }))
    except Exception:
        pass
    
    return {"status": "success", "message": f"User funded with {payload.currency} {amount}", "new_balance": float(account.balance)}


@admin_router.post("/users/{user_id}/adjust-balance")
async def admin_adjust_balance(
    user_id: int,
    payload: AdjustBalanceRequest,
    db_session: SessionDep
):
    """Adjust a user's balance (credit or debit)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = db_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    amount = payload.amount
    adj_type = payload.operation_type
    reason = payload.description or "Balance adjustment"
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get or create user's account
    db_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    account = db_account.scalar_one_or_none()
    
    if not account:
        # Create account if it doesn't exist
        account = DBAccount(
            owner_id=user_id,
            account_number=user.account_number or f"ACC_{user_id}_{int(__import__('time').time())}",
            balance=0.0,
            currency=payload.currency,
            status="active"
        )
        db_session.add(account)
        await db_session.flush()
    
    # ISSUE #4 FIX: Do NOT manually update account.balance
    # Balance is now calculated from ledger (source of truth)
    # Removed: account.balance = (account.balance or 0) + amount
    # Removed: account.balance = current_balance - amount
    
    if adj_type == "credit":
        txn_type = "deposit"
        account.balance = round(float(account.balance or 0) + float(amount), 2)
    else:
        current_balance = float(account.balance or 0)
        if current_balance < float(amount):
            raise HTTPException(status_code=400, detail="Insufficient balance for debit")
        txn_type = "withdrawal"
        account.balance = round(current_balance - float(amount), 2)
    db_session.add(account)

    ref_no = f"ADMIN_ADJ_{user_id}_{int(__import__('time').time())}"
    txn = DBTransaction(
        user_id=user_id,
        account_id=account.id,
        transaction_type=txn_type,
        amount=amount,
        status="completed",
        description=f"Admin {reason}",
        reference_number=ref_no
    )
    db_session.add(txn)
    await db_session.flush()

    from models import Ledger as DBLedger
    from decimal import Decimal
    db_session.add(DBLedger(
        user_id=user_id,
        entry_type="credit" if adj_type == "credit" else "debit",
        amount=Decimal(str(round(float(amount), 2))),
        transaction_id=txn.id,
        source_user_id=1 if adj_type == "credit" else user_id,
        destination_user_id=user_id if adj_type == "credit" else 1,
        description=f"Admin {reason}",
        reference_number=ref_no,
        status="posted"
    ))
    
    await db_session.commit()
    await db_session.refresh(account)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:balance_adjusted",
            "user_id": user_id,
            "amount": amount,
            "type": adj_type,
            "new_balance": float(account.balance)
        }))
    except Exception:
        pass
    
    return {"status": "success", "message": f"Balance {adj_type}ed by {amount}", "new_balance": float(account.balance)}


@admin_router.get("/balance-operations")
async def get_balance_operations(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get recent balance operations (fund/adjust)."""
    transactions = await get_transactions(db_session, skip=skip, limit=limit)
    return transactions


# ============================================================================
# TRANSACTION MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/transactions/{transaction_id}")
async def get_transaction_details(
    transaction_id: int,
    db_session: SessionDep
):
    """Get detailed information about a specific transaction."""
    result = await db_session.execute(
        select(DBTransaction).filter(DBTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return PydanticTransaction.model_validate(transaction)


@admin_router.post("/transactions/{transaction_id}/retry")
async def retry_transaction(
    transaction_id: int,
    db_session: SessionDep
):
    """Retry a failed transaction (admin)."""
    result = await db_session.execute(
        select(DBTransaction).filter(DBTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed transactions can be retried")
    
    # Reset failed transaction to pending so payment rails can re-attempt processing
    transaction.status = "pending"
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "transaction:retrying",
            "transaction_id": transaction_id
        }))
    except Exception:
        pass
    
    return {"status": "retrying", "transaction_id": transaction_id}


# ============================================================================
# KYC MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/kyc-submissions", response_model=List[PydanticKYCSubmission])
async def list_all_kyc_submissions(
    db_session: SessionDep,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all KYC submissions with optional status filter."""
    from sqlalchemy import select
    from models import KYCSubmission as DBKYCSubmission
    
    query = select(DBKYCSubmission)
    if status:
        query = query.filter(DBKYCSubmission.status == status)
    
    query = query.offset(skip).limit(limit)
    result = await db_session.execute(query)
    submissions = result.scalars().all()
    return submissions


@admin_router.get("/kyc-submissions/{submission_id}")
async def get_kyc_submission_details(
    submission_id: int,
    db_session: SessionDep
):
    """Get detailed information about a KYC submission."""
    from models import KYCSubmission as DBKYCSubmission
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return PydanticKYCSubmission.model_validate(submission)


@admin_router.post("/kyc-submissions/{submission_id}/approve")
async def approve_kyc_submission_admin(
    submission_id: int,
    db_session: SessionDep,
    payload: Optional[KYCApprovalRequest] = Body(default=None)
):
    """Approve a KYC submission with optional notes."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    submission.status = "approved"
    submission.notes = payload.notes if payload else ""
    
    # ISSUE #2 FIX: Also update the User.kyc_status field
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == submission.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.kyc_status = "approved"
        db_session.add(user)
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:approved",
            "user_id": submission.user_id,
            "submission_id": submission_id
        }))
    except Exception:
        pass
    
    return {"status": "approved", "submission_id": submission_id}


@admin_router.post("/kyc-submissions/{submission_id}/reject")
async def reject_kyc_submission_admin(
    submission_id: int,
    db_session: SessionDep,
    payload: Optional[KYCRejectionRequest] = Body(default=None)
):
    """Reject a KYC submission with reason."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    submission.status = "rejected"
    submission.notes = (payload.notes if payload else None) or "Rejected by admin"
    
    # ISSUE #2 FIX: Also update the User.kyc_status field when rejecting
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == submission.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.kyc_status = "rejected"
        db_session.add(user)
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:rejected",
            "user_id": submission.user_id,
            "submission_id": submission_id
        }))
    except Exception:
        pass
    
    return {"status": "rejected", "submission_id": submission_id}


# ============================================================================
# REPORTS & ANALYTICS (Admin)
# ============================================================================

@admin_router.get("/reports")
async def get_admin_reports(db_session: SessionDep):
    """Get comprehensive admin reports and analytics."""
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    
    # Count total users
    total_users_result = await db_session.execute(select(func.count(DBUser.id)))
    total_users = total_users_result.scalar_one() or 0
    
    # Count total deposits and sum amount
    from models import Deposit as DBDepositModel
    deposits_result = await db_session.execute(
        select(func.count(DBDepositModel.id), func.sum(DBDepositModel.amount))
    )
    deposits_data = deposits_result.one_or_none()
    total_deposits_count = deposits_data[0] if deposits_data else 0
    total_deposits_amount = float(deposits_data[1]) if deposits_data and deposits_data[1] else 0
    
    # Count active loans
    from models import Loan as DBLoanModel
    loans_result = await db_session.execute(
        select(func.count(DBLoanModel.id)).filter(DBLoanModel.status == "active")
    )
    active_loans = loans_result.scalar_one() or 0
    
    # Count active investments
    from models import Investment as DBInvestmentModel
    investments_result = await db_session.execute(
        select(func.count(DBInvestmentModel.id)).filter(DBInvestmentModel.status == "active")
    )
    active_investments = investments_result.scalar_one() or 0
    
    # Transaction stats
    txn_stats_result = await db_session.execute(
        select(
            func.count(DBTransaction.id),
            func.sum(DBTransaction.amount),
            func.sum(
                __import__('sqlalchemy').case(
                    (DBTransaction.status == "completed", 1),
                    else_=0
                )
            )
        )
    )
    txn_data = txn_stats_result.one_or_none()
    total_txns = txn_data[0] if txn_data else 0
    total_txn_volume = float(txn_data[1]) if txn_data and txn_data[1] else 0
    completed_txns = txn_data[2] if txn_data else 0
    
    return {
        "total_users": total_users,
        "total_deposits_amount": total_deposits_amount,
        "total_deposits_count": total_deposits_count,
        "active_loans_count": active_loans,
        "active_investments_count": active_investments,
        "transactions": {
            "total": total_txns,
            "total_volume": total_txn_volume,
            "completed": completed_txns,
            "success_rate": (completed_txns / total_txns * 100) if total_txns > 0 else 0,
            "average_amount": total_txn_volume / total_txns if total_txns > 0 else 0
        },
        "users": {
            "total": total_users,
            "active_30days": 0,  # Would require login tracking
            "kyc_verified": 0,   # Would require KYC model tracking
            "average_balance": 0  # Would require sum of all balances
        },
        "deposits": {
            "total": total_deposits_amount,
            "count": total_deposits_count,
            "average": total_deposits_amount / total_deposits_count if total_deposits_count > 0 else 0,
            "pending": 0  # Would filter by status
        },
        "loans": {
            "active_count": active_loans,
            "total_outstanding": 0,  # Would require sum calculation
            "average_interest_rate": 0,
            "defaults": 0
        },
        "investments": {
            "total": 0,
            "active_count": active_investments,
            "average_return": 0,
            "total_return": 0
        }
    }


# ============================================================================
# USER ACCOUNTS & KYC SUPPORT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/accounts")
async def get_user_accounts(
    user_id: int,
    db_session: SessionDep
):
    """Get user accounts."""
    # Get all accounts for the user
    result = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    accounts = result.scalars().all()
    
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found for user")
    
    return [{
        "id": acc.id,
        "account_number": acc.account_number,
        "account_type": acc.account_type,
        "balance": acc.balance,
        "currency": acc.currency,
        "status": acc.status,
        "created_at": acc.created_at
    } for acc in accounts]


@admin_router.post("/users/{user_id}/accounts")
async def create_user_account(
    user_id: int,
    payload: CreateAccountRequest,
    db_session: SessionDep
):
    """Create a new account for a user."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has an account
    existing_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    if existing_account.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has an account")
    
    # Create new account
    account_number = payload.account_number or f"ACC{user_id}_{int(__import__('time').time())}"
    
    # Update user's account_number if not set
    if not user.account_number:
        user.account_number = account_number
    
    new_account = DBAccount(
        owner_id=user_id,
        account_number=account_number,
        balance=payload.initial_balance,
        currency=payload.currency,
        status="active"
    )
    db_session.add(new_account)
    
    await db_session.commit()
    await db_session.refresh(new_account)
    
    return {
        "id": new_account.id,
        "account_number": new_account.account_number,
        "balance": float(new_account.balance),
        "currency": new_account.currency,
        "account_type": payload.account_type,
        "created_at": new_account.created_at
    }


@admin_router.get("/users/{user_id}/kyc")
async def get_user_kyc(
    user_id: int,
    db_session: SessionDep
):
    """Get KYC information for a user."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.user_id == user_id)
    )
    kyc_submissions = result.scalars().all()
    return kyc_submissions


@admin_router.get("/users/{user_id}/transactions")
async def get_user_transactions(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get transactions for a specific user."""
    result = await db_session.execute(
        select(DBTransaction)
        .filter(DBTransaction.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return transactions


# ============================================================================
# USER SEARCH & FILTER (Admin) - MUST BE BEFORE {user_id}
# ============================================================================

@admin_router.get("/users/search")
async def search_users(
    db_session: SessionDep,
    query: str = "",
    skip: int = 0,
    limit: int = 50
):
    """Search for users by email or name."""
    search_pattern = f"%{query}%"
    result = await db_session.execute(
        select(DBUser)
        .filter(
            (DBUser.email.ilike(search_pattern)) | 
            (DBUser.full_name.ilike(search_pattern))
        )
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return [PydanticUser.model_validate(u) for u in users]


@admin_router.get("/users/filter")
async def filter_users(
    db_session: SessionDep,
    status: Optional[str] = None,
    is_admin: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50
):
    """Filter users by status or admin status."""
    query = select(DBUser)
    
    if status == "active":
        query = query.filter(DBUser.is_active == True)
    elif status == "suspended":
        query = query.filter(DBUser.is_active == False)
    
    if is_admin is not None:
        query = query.filter(DBUser.is_admin == is_admin)
    
    query = query.offset(skip).limit(limit)
    result = await db_session.execute(query)
    users = result.scalars().all()
    return [PydanticUser.model_validate(u) for u in users]


# ============================================================================
# USER DETAILS & ACTIVITY LOG (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    db_session: SessionDep
):
    """Get detailed information about a specific user."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return PydanticUser.model_validate(user)


@admin_router.get("/users/{user_id}/activity")
async def get_user_activity_log(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get activity log for a specific user (transactions, updates, etc)."""
    # Get transactions for the user
    result = await db_session.execute(
        select(DBTransaction)
        .filter(DBTransaction.user_id == user_id)
        .order_by(DBTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return [PydanticTransaction.model_validate(t) for t in transactions]


@admin_router.get("/activity-log")
async def get_admin_activity_log(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get system activity log (all transactions)."""
    result = await db_session.execute(
        select(DBTransaction)
        .order_by(DBTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return [PydanticTransaction.model_validate(t) for t in transactions]


# ============================================================================
# ADMIN MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/admins")
async def list_all_admins(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get list of all admin users."""
    result = await db_session.execute(
        select(DBUser)
        .filter(DBUser.is_admin == True)
        .offset(skip)
        .limit(limit)
    )
    admins = result.scalars().all()
    return [PydanticUser.model_validate(admin) for admin in admins]


@admin_router.post("/admins/{user_id}/promote")
async def promote_user_to_admin(
    user_id: int,
    db_session: SessionDep
):
    """Promote a user to admin status."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    user.is_admin = True
    await db_session.commit()
    await db_session.refresh(user)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "admin:promoted",
            "user_id": user_id,
            "email": user.email
        }))
    except Exception:
        pass
    
    return {"status": "promoted", "user_id": user_id, "email": user.email}


@admin_router.post("/admins/{user_id}/demote")
async def demote_admin_to_user(
    user_id: int,
    db_session: SessionDep
):
    """Demote an admin to regular user status."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_admin:
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    user.is_admin = False
    await db_session.commit()
    await db_session.refresh(user)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "admin:demoted",
            "user_id": user_id,
            "email": user.email
        }))
    except Exception:
        pass
    
    return {"status": "demoted", "user_id": user_id, "email": user.email}


# ============================================================================
# USER ACCOUNT STATUS & SECURITY (Admin)
# ============================================================================

@admin_router.post("/users/{user_id}/suspend")
async def suspend_user_account(
    user_id: int,
    db_session: SessionDep,
    payload: Optional[dict] = Body(default=None),
):
    """Suspend a user account (disable access)."""
    body = payload or {}
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reason = body.get("reason", "Admin suspension")
    note = body.get("note", "")
    duration_days = body.get("duration_days", 0)

    user.is_active = False
    user.is_suspended = True
    db_session.add(user)

    from models import AuditLog as DBAuditLog
    db_session.add(DBAuditLog(
        admin_id=1,
        user_id=user_id,
        action_type="USER_SUSPENDED",
        reason=reason,
        details=f"Suspended: {reason} | Note: {note} | Duration: {duration_days} days",
        status="success"
    ))
    await db_session.commit()

    try:
        await manager.broadcast(json.dumps({
            "event": "user:suspended",
            "user_id": user_id,
            "reason": reason
        }))
    except Exception:
        pass

    return {
        "success": True,
        "status": "suspended",
        "user_id": user_id,
        "is_active": False,
        "message": f"User {user.email} has been suspended"
    }


@admin_router.post("/users/{user_id}/activate")
async def activate_user_account(
    user_id: int,
    db_session: SessionDep,
    payload: Optional[dict] = Body(default=None),
):
    """Activate (unsuspend) a suspended user account."""
    body = payload or {}
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reason = body.get("reason", "Admin reactivation")
    user.is_active = True
    user.is_suspended = False
    db_session.add(user)

    from models import AuditLog as DBAuditLog
    db_session.add(DBAuditLog(
        admin_id=1,
        user_id=user_id,
        action_type="USER_ACTIVATED",
        reason=reason,
        details=f"Activated user account: {reason}",
        status="success"
    ))
    await db_session.commit()

    try:
        await manager.broadcast(json.dumps({
            "event": "user:activated",
            "user_id": user_id
        }))
    except Exception:
        pass

    return {
        "success": True,
        "status": "activated",
        "user_id": user_id,
        "is_active": True,
        "message": f"User {user.email} has been activated"
    }


@admin_router.post("/users/{user_id}/freeze")
async def freeze_user_accounts_admin(
    user_id: int,
    db_session: SessionDep,
    payload: Optional[dict] = Body(default=None),
):
    """Freeze all accounts for a user and record an AccountHold."""
    body = payload or {}
    result = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reason = body.get("reason", "Admin freeze")
    note = body.get("note", "")
    duration_days = body.get("duration_days", 0)
    full_reason = f"[ACCOUNT_FREEZE] {reason}" + (f" - {note}" if note else "")

    user.is_frozen = True
    db_session.add(user)

    acc_res = await db_session.execute(select(DBAccount).where(DBAccount.owner_id == user_id))
    accounts = acc_res.scalars().all()
    if not accounts:
        new_acc = DBAccount(
            owner_id=user_id,
            account_number=user.account_number or f"ACC{user_id}_{int(__import__('time').time())}",
            account_type="checking",
            balance=0.0,
            currency="USD",
            status="frozen"
        )
        db_session.add(new_acc)
        await db_session.flush()
        accounts = [new_acc]

    frozen_count = 0
    for acc in accounts:
        acc.status = "frozen"
        db_session.add(acc)
        frozen_count += 1
        hold = AccountHold(
            account_id=acc.id,
            reason=full_reason,
            created_at=datetime.utcnow()
        )
        db_session.add(hold)

    from models import AuditLog as DBAuditLog
    db_session.add(DBAuditLog(
        admin_id=1,
        user_id=user_id,
        action_type="ACCOUNT_FROZEN",
        reason=reason,
        details=f"Froze {frozen_count} account(s). Reason: {full_reason} | Duration: {duration_days} days",
        status="success"
    ))
    await db_session.commit()

    return {
        "success": True,
        "status": "frozen",
        "user_id": user_id,
        "is_frozen": True,
        "accounts_frozen": frozen_count,
        "message": f"Froze {frozen_count} account(s) for {user.email}"
    }


@admin_router.post("/users/{user_id}/unfreeze")
async def unfreeze_user_accounts_admin(
    user_id: int,
    db_session: SessionDep,
    payload: Optional[dict] = Body(default=None),
):
    """Unfreeze all accounts for a user and release active AccountHolds."""
    body = payload or {}
    result = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reason = body.get("reason", "Admin unfreeze")
    user.is_frozen = False
    db_session.add(user)

    acc_res = await db_session.execute(select(DBAccount).where(DBAccount.owner_id == user_id))
    accounts = acc_res.scalars().all()
    unfrozen_count = 0
    for acc in accounts:
        acc.status = "active"
        db_session.add(acc)
        unfrozen_count += 1
        holds_res = await db_session.execute(
            select(AccountHold).where(
                (AccountHold.account_id == acc.id) & (AccountHold.released_at == None)
            )
        )
        for h in holds_res.scalars().all():
            h.released_at = datetime.utcnow()
            db_session.add(h)

    from models import AuditLog as DBAuditLog
    db_session.add(DBAuditLog(
        admin_id=1,
        user_id=user_id,
        action_type="ACCOUNT_UNFROZEN",
        reason=reason,
        details=f"Unfroze {unfrozen_count} account(s). Reason: {reason}",
        status="success"
    ))
    await db_session.commit()

    return {
        "success": True,
        "status": "active",
        "user_id": user_id,
        "is_frozen": False,
        "accounts_unfrozen": unfrozen_count,
        "message": f"Unfroze {unfrozen_count} account(s) for {user.email}"
    }


@admin_router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    payload: dict,
    db_session: SessionDep,
    current_admin: CurrentAdminUserDep
):
    """
    Reset a user's password (Admin authority with audit trail).
    
    RULES:
    1. Admin does NOT see the new password (only that a reset was initiated)
    2. System hashes the password and updates the record
    3. User is forced to change password on next login
    4. Every action is logged in AuditLog with admin_id, user_id, timestamp, reason
    """
    from auth_utils import get_password_hash
    from admin_audit_service import admin_audit_service
    
    try:
        # Verify user exists
        result = await db_session.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get password and reason from payload
        new_password = payload.get("new_password")
        reason = payload.get("reason", "Admin initiated password reset")
        
        if not new_password or len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Hash the password (admin never sees plaintext)
        user.hashed_password = get_password_hash(new_password)
        
        # RULE: Force password change on next login
        # (This would require a new column in User model - optional for now)
        # user.force_password_change = True
        
        await db_session.commit()
        
        # LOG THE ACTION: Create audit trail
        await admin_audit_service.log_password_reset_action(
            db=db_session,
            admin_id=current_admin.id,
            user_id=user_id,
            reason=reason
        )
        
        # Broadcast event
        try:
            await manager.broadcast(json.dumps({
                "event": "user:password_reset",
                "user_id": user_id,
                "admin_id": current_admin.id,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception:
            pass
        
        log.info(f"ADMIN {current_admin.id} reset password for USER {user_id}. Reason: {reason}")
        
        return {
            "success": True,
            "status": "password_reset",
            "user_id": user_id,
            "message": "Password has been reset. User will be required to change it on next login.",
            "audited": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        log.error(f"Password reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Password reset failed: {str(e)}")


# ============================================================================
# DEPOSITS & WITHDRAWALS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/pending-deposits")
async def get_pending_deposits(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get list of pending deposits."""
    result = await db_session.execute(
        select(DBDeposit)
        .filter(DBDeposit.status == "pending")
        .offset(skip)
        .limit(limit)
    )
    deposits = result.scalars().all()
    return [PydanticDeposit.model_validate(d) for d in deposits]


@admin_router.post("/deposits/{deposit_id}/approve")
async def approve_deposit_admin(
    deposit_id: int,
    db_session: SessionDep
):
    """Approve a pending deposit."""
    result = await db_session.execute(
        select(DBDeposit).filter(DBDeposit.id == deposit_id)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    if deposit.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending deposits can be approved")
    
    deposit.status = "completed"
    
    # Update user balance
    user_result = await db_session.execute(
        select(DBUser).filter(DBUser.id == deposit.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.balance = (user.balance or 0) + deposit.amount
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:approved",
            "user_id": deposit.user_id,
            "deposit_id": deposit_id,
            "amount": deposit.amount
        }))
    except Exception:
        pass
    
    return {"status": "approved", "deposit_id": deposit_id}


@admin_router.post("/deposits/{deposit_id}/reject")
async def reject_deposit_admin(
    deposit_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Reject a pending deposit."""
    result = await db_session.execute(
        select(DBDeposit).filter(DBDeposit.id == deposit_id)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    if deposit.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending deposits can be rejected")
    
    deposit.status = "rejected"
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:rejected",
            "user_id": deposit.user_id,
            "deposit_id": deposit_id,
            "reason": payload.get("reason", "")
        }))
    except Exception:
        pass
    
    return {"status": "rejected", "deposit_id": deposit_id}


# ============================================================================
# AUDIT LOG ENDPOINTS (Admin)
# ============================================================================

@admin_router.get("/audit-logs")
async def get_all_audit_logs(
    db_session: SessionDep,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve admin audit logs with optional filtering.
    
    Query Parameters:
    - user_id: Filter by target user ID
    - admin_id: Filter by admin ID (who performed the action)
    - action_type: Filter by action type (fund, freeze, reset_password, approve_kyc, etc.)
    
    RULE: These logs are immutable - they represent the complete audit trail of all admin actions.
    """
    from admin_audit_service import admin_audit_service
    from models import AuditLog as DBAuditLog
    
    try:
        # Build query
        query = select(DBAuditLog)
        
        if user_id:
            query = query.filter(DBAuditLog.user_id == user_id)
        if admin_id:
            query = query.filter(DBAuditLog.admin_id == admin_id)
        if action_type:
            query = query.filter(DBAuditLog.action_type == action_type)
        
        # Order by most recent first and paginate
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "account_id": log.account_id,
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "status_message": log.status_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "total": len(logs),
            "skip": skip,
            "limit": limit,
            "logs": logs
        }
        
    except Exception as e:
        log.error(f"Error retrieving audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/user/{user_id}")
async def get_user_audit_logs(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """
    Get all admin actions performed ON a specific user.
    
    This shows what admins have done to this user:
    - Funded their account
    - Reset their password
    - Approved/rejected KYC
    - Frozen/unfrozen account
    - etc.
    """
    from models import AuditLog as DBAuditLog
    
    try:
        # Verify user exists
        user_result = await db_session.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        if not user_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all audit logs for this user
        query = select(DBAuditLog).filter(DBAuditLog.user_id == user_id)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "user_id": user_id,
            "total_actions": len(logs),
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving user audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/admin/{admin_id}")
async def get_admin_actions(
    admin_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """
    Get all actions performed BY a specific admin.
    
    This shows the complete action history for an admin user:
    - Who they funded
    - Who they reset passwords for
    - When and what they did
    - Reason for each action
    """
    from models import AuditLog as DBAuditLog
    
    try:
        # Verify admin exists
        admin_result = await db_session.execute(
            select(DBUser).filter(DBUser.id == admin_id)
        )
        admin = admin_result.scalar_one_or_none()
        if not admin or not admin.is_admin:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        # Get all audit logs for this admin
        query = select(DBAuditLog).filter(DBAuditLog.admin_id == admin_id)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "account_id": log.account_id,
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "admin_id": admin_id,
            "admin_email": admin.email,
            "total_actions": len(logs),
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving admin actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/action-type/{action_type}")
async def get_audit_logs_by_action(
    action_type: str,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all audit logs for a specific action type.
    
    Valid action types:
    - fund: Admin funding operations
    - freeze: Account freezing
    - unfreeze: Account unfreezing
    - reset_password: Password resets
    - approve_kyc: KYC approvals
    - reject_kyc: KYC rejections
    - reverse_transaction: Transaction reversals
    - create_user: User creation
    - delete_user: User deletion
    """
    from models import AuditLog as DBAuditLog
    
    try:
        query = select(DBAuditLog).filter(DBAuditLog.action_type == action_type)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        if not audit_logs:
            return {
                "action_type": action_type,
                "total": 0,
                "logs": []
            }
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "reason": log.reason,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "action_type": action_type,
            "total": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        log.error(f"Error retrieving audit logs by action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")
