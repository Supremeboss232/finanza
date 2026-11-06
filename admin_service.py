"""
Admin Service Module
Centralizes all admin operations and data handling without JSON dependencies.
Provides pure Python functions for all admin tasks.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, or_, and_
from datetime import datetime
from decimal import Decimal
import logging
import uuid

from models import (
    User as DBUser,
    Transaction as DBTransaction,
    FormSubmission as DBFormSubmission,
    KYCSubmission as DBKYCSubmission,
    KYCInfo as DBKYCInfo,
    Card as DBCard,
    Deposit as DBDeposit,
    Loan as DBLoan,
    Investment as DBInvestment,
    Account as DBAccount,
    Ledger as DBLedger,
    Notification as DBNotification
)

from schemas import (
    User as PydanticUser,
    Transaction as PydanticTransaction,
    FormSubmission as PydanticFormSubmission,
    KYCSubmission as PydanticKYCSubmission,
    Card as PydanticCard,
    Deposit as PydanticDeposit,
    Loan as PydanticLoan,
    Investment as PydanticInvestment,
    UserCreate,
    AdminDashboardMetrics,
    FundUserRequest,
    FundUserResponse,
    AdjustBalanceRequest
)

from crud import (
    get_users, create_user, get_transactions, get_form_submissions,
    get_user_by_username, get_user_by_email, get_kyc_submissions,
    get_pending_kyc_submissions, approve_kyc_submission, reject_kyc_submission,
    get_user_cards, create_user_card, get_card, get_user,
    get_user_deposits, create_user_deposit, get_deposit,
    get_user_loans, create_user_loan, get_loan,
    get_user_investments, create_user_investment, get_investment
)

from auth_utils import get_password_hash
from system_fund_service import SystemFundService
from config import settings
from balance_service_ledger import BalanceServiceLedger

log = logging.getLogger(__name__)


class AdminService:
    """Service class for all admin operations"""

    # ==================== USER MANAGEMENT ====================

    async def get_all_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all users with accurate balance and primary account information.
        """
        users = await get_users(db, skip=skip, limit=limit)
        result = []

        balance_cache = {}
        account_num_cache = {}
        for user in users:
            balance_cache[user.id] = await BalanceServiceLedger.get_user_balance(db, user.id)
            acc_res = await db.execute(select(DBAccount).where(DBAccount.owner_id == user.id))
            acc = acc_res.scalars().first()
            account_num_cache[user.id] = acc.account_number if acc else user.account_number

        for user in users:
            user_dict = PydanticUser.model_validate(user).model_dump()
            user_dict['balance'] = balance_cache[user.id]
            if not user_dict.get('account_number') and account_num_cache.get(user.id):
                user_dict['account_number'] = account_num_cache[user.id]
            result.append(user_dict)
        return result

    async def create_new_user(self, db: AsyncSession, user_data: UserCreate) -> PydanticUser:
        """Create a new user"""
        existing = await get_user_by_username(db, username=user_data.email)
        if existing:
            raise ValueError("Email already registered")

        created = await create_user(db=db, user=user_data)
        return PydanticUser.model_validate(created)

    async def get_user_by_id_admin(self, db: AsyncSession, user_id: int) -> PydanticUser:
        """Get a specific user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return PydanticUser.model_validate(user)

    async def update_user(self, db: AsyncSession, user_id: int, updates: Dict[str, Any]) -> PydanticUser:
        """Update user fields"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        for key, value in updates.items():
            if key == "password" and value:
                hashed = get_password_hash(value)
                setattr(user, "hashed_password", hashed)
            elif hasattr(user, key):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return PydanticUser.model_validate(user)

    async def delete_user(self, db: AsyncSession, user_id: int) -> Dict[str, str]:
        """Delete a user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        await db.delete(user)
        await db.commit()
        return {"message": f"User {user_id} deleted successfully"}

    async def set_admin_status(self, db: AsyncSession, user_id: int, is_admin: bool) -> PydanticUser:
        """Set admin status for a user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.is_admin = is_admin
        await db.commit()
        await db.refresh(user)
        return PydanticUser.model_validate(user)

    # ==================== TRANSACTION MANAGEMENT ====================

    async def get_all_transactions(self, db: AsyncSession, skip: int = 0, limit: int = 100, status_filter: str = None) -> List[Dict[str, Any]]:
        """Retrieve all transactions with proper user details."""
        query = select(DBTransaction)

        if status_filter == 'completed':
            query = query.where(DBTransaction.status == 'completed')
        elif status_filter == 'pending_or_blocked':
            query = query.where(
                or_(
                    DBTransaction.status == 'pending',
                    DBTransaction.status == 'blocked'
                )
            )

        query = query.order_by(DBTransaction.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        transactions = result.scalars().all()

        output = []
        for t in transactions:
            user = await get_user(db, user_id=t.user_id) if t.user_id else None
            user_email = user.email if user else "N/A"
            kyc_status = user.kyc_status if user and getattr(user, 'kyc_status', None) else "not_submitted"

            try:
                tx_data = PydanticTransaction.model_validate(t)
                tx_dict = tx_data.model_dump()
                tx_dict['user'] = {'email': user_email, 'full_name': user.full_name if user else 'N/A'}
                tx_dict['user_email'] = user_email
                tx_dict['status_label'] = self._get_status_label(t.status)
                tx_dict['kyc_status_at_time'] = kyc_status
                output.append(tx_dict)
            except Exception:
                data = {
                    'id': t.id,
                    'user_id': t.user_id,
                    'account_id': t.account_id,
                    'amount': float(t.amount or 0),
                    'transaction_type': t.transaction_type,
                    'status': t.status,
                    'status_label': self._get_status_label(t.status),
                    'description': getattr(t, 'description', None),
                    'reference_number': getattr(t, 'reference_number', None),
                    'created_at': t.created_at,
                    'kyc_status_at_time': kyc_status,
                    'user_email': user_email,
                    'user': {'email': user_email, 'full_name': user.full_name if user else 'N/A'}
                }
                output.append(data)

        return output

    @staticmethod
    def _get_status_label(status: str) -> str:
        """Get user-friendly label for transaction status"""
        labels = {
            'completed': '[OK] Completed',
            'pending': '[..] Pending',
            'blocked': '[NO] Blocked',
            'failed': '[FAIL] Failed',
            'cancelled': 'Cancelled'
        }
        return labels.get(status, status)

    async def get_recent_transactions(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions from DBTransaction and DBLedger."""
        tx_query = (
            select(DBTransaction, DBUser.email, DBAccount.account_number)
            .outerjoin(DBUser, DBTransaction.user_id == DBUser.id)
            .outerjoin(DBAccount, DBTransaction.account_id == DBAccount.id)
            .order_by(DBTransaction.created_at.desc())
            .limit(limit)
        )
        tx_result = await db.execute(tx_query)
        rows = tx_result.all()

        transactions = []
        for txn, email, account_num in rows:
            transactions.append({
                'id': txn.id,
                'user_id': txn.user_id,
                'user_email': email or "SYSTEM",
                'amount': float(txn.amount or 0),
                'type': (txn.transaction_type or "transfer").upper(),
                'transaction_type': txn.transaction_type or "transfer",
                'description': txn.description or "",
                'reference_number': txn.reference_number or "",
                'status': txn.status or "completed",
                'account_number': account_num or "N/A",
                'created_at': txn.created_at.isoformat() if txn.created_at else None
            })
        return transactions

    # ==================== KYC MANAGEMENT ====================

    async def get_kyc_submissions_list(self, db: AsyncSession) -> List[PydanticKYCSubmission]:
        """Get all KYC submissions"""
        submissions = await get_kyc_submissions(db)
        return [PydanticKYCSubmission.model_validate(s) for s in submissions]

    async def get_pending_kyc(self, db: AsyncSession) -> List[PydanticKYCSubmission]:
        """Get pending KYC submissions"""
        submissions = await get_pending_kyc_submissions(db)
        return [PydanticKYCSubmission.model_validate(s) for s in submissions]

    async def approve_kyc(self, db: AsyncSession, submission_id: int, notes: str = "") -> Dict[str, Any]:
        """Approve a KYC submission (by submission_id OR user_id) and sync User + KYCInfo + KYCSubmission records"""
        # 1. Look for a pending KYCSubmission by id first, then by user_id
        sub_res = await db.execute(
            select(DBKYCSubmission).where(
                and_(DBKYCSubmission.id == submission_id, DBKYCSubmission.status == "pending")
            )
        )
        sub = sub_res.scalar_one_or_none()

        if not sub:
            sub_by_user_pending = await db.execute(
                select(DBKYCSubmission)
                .where(and_(DBKYCSubmission.user_id == submission_id, DBKYCSubmission.status == "pending"))
                .order_by(DBKYCSubmission.submitted_at.desc())
            )
            sub = sub_by_user_pending.scalars().first()

        if not sub:
            sub_any = await db.execute(select(DBKYCSubmission).where(DBKYCSubmission.id == submission_id))
            sub = sub_any.scalar_one_or_none()

        if not sub:
            sub_by_user_any = await db.execute(
                select(DBKYCSubmission)
                .where(DBKYCSubmission.user_id == submission_id)
                .order_by(DBKYCSubmission.submitted_at.desc())
            )
            sub = sub_by_user_any.scalars().first()

        target_user_ids = set()
        if sub and sub.user_id:
            target_user_ids.add(sub.user_id)

        # Also check if submission_id directly matches a User ID (e.g., from admin_users.html)
        u_direct_res = await db.execute(select(DBUser).where(DBUser.id == submission_id))
        u_direct = u_direct_res.scalar_one_or_none()
        if u_direct and (not sub or u_direct.kyc_status in ("pending", "not_started", "submitted")):
            target_user_ids.add(u_direct.id)

        if not sub and not target_user_ids:
            raise ValueError(f"KYC submission or user {submission_id} not found")

        now = datetime.utcnow()
        if sub:
            sub.status = "approved"
            sub.reviewed_at = now
            db.add(sub)

        primary_user_id = sub.user_id if sub else next(iter(target_user_ids))

        for uid in target_user_ids:
            # Update all KYCSubmission rows for this user
            all_subs_res = await db.execute(select(DBKYCSubmission).where(DBKYCSubmission.user_id == uid))
            user_subs = all_subs_res.scalars().all()
            if not user_subs:
                new_sub = DBKYCSubmission(
                    user_id=uid,
                    document_type="passport",
                    document_file_path="/img/logo.png",
                    status="approved",
                    submitted_at=now,
                    reviewed_at=now,
                )
                db.add(new_sub)
                if not sub:
                    sub = new_sub
            else:
                for usub in user_subs:
                    usub.status = "approved"
                    usub.reviewed_at = now
                    db.add(usub)
                    if not sub:
                        sub = usub

            # Update User record
            u_res = await db.execute(select(DBUser).where(DBUser.id == uid))
            u = u_res.scalar_one_or_none()
            if u:
                u.kyc_status = "approved"
                u.is_verified = True
                u.is_active = True
                if hasattr(u, "kyc_verified"):
                    u.kyc_verified = True
                db.add(u)

            # Unlock user's accounts
            acc_res = await db.execute(select(DBAccount).where(DBAccount.owner_id == uid))
            for acc in acc_res.scalars().all():
                acc.status = "active"
                acc.kyc_level = "full"
                db.add(acc)

            # Update KYCInfo record if present
            info_res = await db.execute(select(DBKYCInfo).where(DBKYCInfo.user_id == uid))
            info = info_res.scalar_one_or_none()
            if info:
                info.status = "approved"
                info.kyc_status = "approved"
                info.rejection_reason = None
                info.submission_locked = False
                info.approved_at = now
                info.reviewed_at = now
                db.add(info)

            notif = DBNotification(
                user_id=uid,
                title="KYC Verification Approved",
                message="Your identity verification has been approved. Full banking privileges are now active.",
                notification_type="kyc",
                is_read=False
            )
            db.add(notif)

        await db.commit()
        return {
            "message": "KYC verification approved",
            "id": (sub.id if sub and sub.id else submission_id),
            "user_id": primary_user_id,
            "status": "approved"
        }

    async def reject_kyc(self, db: AsyncSession, submission_id: int, reason: str = "") -> Dict[str, Any]:
        """Reject a KYC submission (by submission_id OR user_id) and sync User + KYCInfo + KYCSubmission records"""
        sub_res = await db.execute(
            select(DBKYCSubmission).where(
                and_(DBKYCSubmission.id == submission_id, DBKYCSubmission.status == "pending")
            )
        )
        sub = sub_res.scalar_one_or_none()

        if not sub:
            sub_by_user_pending = await db.execute(
                select(DBKYCSubmission)
                .where(and_(DBKYCSubmission.user_id == submission_id, DBKYCSubmission.status == "pending"))
                .order_by(DBKYCSubmission.submitted_at.desc())
            )
            sub = sub_by_user_pending.scalars().first()

        if not sub:
            sub_any = await db.execute(select(DBKYCSubmission).where(DBKYCSubmission.id == submission_id))
            sub = sub_any.scalar_one_or_none()

        if not sub:
            sub_by_user_any = await db.execute(
                select(DBKYCSubmission)
                .where(DBKYCSubmission.user_id == submission_id)
                .order_by(DBKYCSubmission.submitted_at.desc())
            )
            sub = sub_by_user_any.scalars().first()

        target_user_ids = set()
        if sub and sub.user_id:
            target_user_ids.add(sub.user_id)

        u_direct_res = await db.execute(select(DBUser).where(DBUser.id == submission_id))
        u_direct = u_direct_res.scalar_one_or_none()
        if u_direct and (not sub or u_direct.kyc_status in ("pending", "not_started", "submitted")):
            target_user_ids.add(u_direct.id)

        if not sub and not target_user_ids:
            raise ValueError(f"KYC submission or user {submission_id} not found")

        now = datetime.utcnow()
        if sub:
            sub.status = "rejected"
            sub.reviewed_at = now
            db.add(sub)

        primary_user_id = sub.user_id if sub else next(iter(target_user_ids))

        for uid in target_user_ids:
            all_subs_res = await db.execute(select(DBKYCSubmission).where(DBKYCSubmission.user_id == uid))
            user_subs = all_subs_res.scalars().all()
            if not user_subs:
                new_sub = DBKYCSubmission(
                    user_id=uid,
                    document_type="passport",
                    document_file_path="/img/logo.png",
                    status="rejected",
                    submitted_at=now,
                    reviewed_at=now,
                )
                db.add(new_sub)
                if not sub:
                    sub = new_sub
            else:
                for usub in user_subs:
                    usub.status = "rejected"
                    usub.reviewed_at = now
                    db.add(usub)
                    if not sub:
                        sub = usub

            u_res = await db.execute(select(DBUser).where(DBUser.id == uid))
            u = u_res.scalar_one_or_none()
            if u:
                u.kyc_status = "rejected"
                if hasattr(u, "kyc_verified"):
                    u.kyc_verified = False
                db.add(u)

            info_res = await db.execute(select(DBKYCInfo).where(DBKYCInfo.user_id == uid))
            info = info_res.scalar_one_or_none()
            if info:
                info.status = "rejected"
                info.kyc_status = "rejected"
                info.rejection_reason = reason or "Verification criteria not met"
                info.submission_locked = False
                info.reviewed_at = now
                db.add(info)

            notif = DBNotification(
                user_id=uid,
                title="KYC Verification Update",
                message=f"Your KYC verification requires attention: {reason or 'Please re-submit clear identity documents.'}",
                notification_type="kyc",
                is_read=False
            )
            db.add(notif)

        await db.commit()
        return {
            "message": "KYC submission rejected",
            "id": (sub.id if sub and sub.id else submission_id),
            "user_id": primary_user_id,
            "status": "rejected",
            "reason": reason
        }

    # ==================== DASHBOARD METRICS ====================

    async def get_dashboard_metrics(self, db: AsyncSession) -> AdminDashboardMetrics:
        """
        Get comprehensive dashboard metrics across Users, Accounts, Transactions, Ledger, and KYC.
        """
        try:
            total_users = await db.scalar(select(func.count(DBUser.id))) or 0

            total_deposits = await BalanceServiceLedger.get_admin_total_deposits(db)
            total_volume = await BalanceServiceLedger.get_admin_total_volume(db)

            pending_sub_count = await db.scalar(
                select(func.count(distinct(DBKYCSubmission.user_id))).where(
                    DBKYCSubmission.status == "pending"
                )
            ) or 0
            pending_user_count = await db.scalar(
                select(func.count(DBUser.id)).where(
                    DBUser.kyc_status == "pending"
                )
            ) or 0
            pending_kyc_count = max(pending_sub_count, pending_user_count)

            tx_count = await db.scalar(select(func.count(DBTransaction.id))) or 0
            ledger_count = await db.scalar(
                select(func.count(DBLedger.id)).where(DBLedger.status == "posted")
            ) or 0
            transaction_count = max(tx_count, ledger_count)

            recent_users_result = await db.execute(
                select(DBUser).order_by(DBUser.created_at.desc()).limit(5)
            )
            recent_users = [PydanticUser.model_validate(u) for u in recent_users_result.scalars()]

            recent_tx_list = await self.get_recent_transactions(db, limit=5)

            return AdminDashboardMetrics(
                total_users=total_users,
                pending_kyc=pending_kyc_count,
                total_transactions=transaction_count,
                total_deposits=total_deposits,
                total_volume=total_volume,
                recent_users=recent_users,
                recent_transactions=recent_tx_list
            )
        except Exception as e:
            log.error(f"Error calculating dashboard metrics: {e}")
            raise

    async def get_top_users_by_balance(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users ranked by balance."""
        all_users_result = await db.execute(select(DBUser))
        all_users = all_users_result.scalars().all()

        user_balances = []
        for user in all_users:
            balance = await BalanceServiceLedger.get_user_balance(db, user.id)
            if balance > 0:
                user_balances.append({
                    'rank': 0,
                    'user_id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'balance': balance,
                    'status': 'Active' if user.is_active else 'Inactive'
                })

        user_balances.sort(key=lambda x: x['balance'], reverse=True)
        for idx, user_info in enumerate(user_balances[:limit], 1):
            user_info['rank'] = idx

        return user_balances[:limit]

    # ==================== FORM SUBMISSIONS ====================

    async def get_all_forms(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[PydanticFormSubmission]:
        """Get all form submissions"""
        submissions = await get_form_submissions(db, skip=skip, limit=limit)
        return submissions

    # ==================== FUND OPERATIONS ====================

    async def fund_user_account(
        self,
        db: AsyncSession,
        fund_request: FundUserRequest,
        admin_user_id: int
    ) -> FundUserResponse:
        """Fund a user account and update Account, Transaction, and Ledger."""
        try:
            user = await get_user_by_email(db, email=fund_request.email)
            if not user:
                raise ValueError(f"User with email {fund_request.email} not found")

            account_result = await db.execute(
                select(DBAccount).filter(DBAccount.owner_id == user.id)
            )
            account = account_result.scalars().first()
            if not account:
                account = DBAccount(
                    owner_id=user.id,
                    account_number=user.account_number or f"ACC{user.id}001",
                    account_type="checking",
                    balance=0.0,
                    currency="USD",
                    status="active"
                )
                db.add(account)
                await db.flush()

            amount = float(fund_request.amount)
            account.balance = round(float(account.balance or 0) + amount, 2)
            db.add(account)

            ref_num = f"FUND-{uuid.uuid4().hex[:10].upper()}"
            reason = fund_request.notes or f"Admin funding from {fund_request.fund_source}"

            tx = DBTransaction(
                user_id=user.id,
                account_id=account.id,
                transaction_type="admin_fund",
                amount=amount,
                status="completed",
                description=reason,
                reference_number=ref_num
            )
            db.add(tx)
            await db.flush()

            ledger_entry = DBLedger(
                user_id=user.id,
                entry_type="credit",
                amount=Decimal(str(round(amount, 2))),
                transaction_id=tx.id,
                source_user_id=admin_user_id or 1,
                destination_user_id=user.id,
                description=reason,
                reference_number=ref_num,
                status="posted"
            )
            db.add(ledger_entry)
            await db.commit()

            return FundUserResponse(
                success=True,
                message=f"Successfully funded {user.email} with ${amount:,.2f}.",
                transaction_id=tx.id,
                user_id=user.id
            )
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to fund account: {str(e)}")

    async def adjust_balance(
        self,
        db: AsyncSession,
        adjust_request: AdjustBalanceRequest
    ) -> Dict[str, Any]:
        """Adjust user balance and update Account, Transaction, and Ledger."""
        user = await get_user_by_email(db, email=adjust_request.email)
        if not user:
            raise ValueError(f"User with email {adjust_request.email} not found")

        acc_res = await db.execute(select(DBAccount).where(DBAccount.owner_id == user.id))
        account = acc_res.scalars().first()
        if not account:
            account = DBAccount(
                owner_id=user.id,
                account_number=user.account_number or f"ACC{user.id}001",
                account_type="checking",
                balance=0.0,
                currency="USD",
                status="active"
            )
            db.add(account)
            await db.flush()

        amount = float(adjust_request.amount)
        op_type = getattr(adjust_request, "operation_type", "credit") or "credit"
        if op_type == "debit":
            if float(account.balance or 0) < amount:
                raise ValueError("Insufficient balance for debit")
            account.balance = round(float(account.balance or 0) - amount, 2)
        else:
            account.balance = round(float(account.balance or 0) + amount, 2)
        db.add(account)

        ref_num = f"ADJ-{uuid.uuid4().hex[:10].upper()}"
        reason = adjust_request.reason or "Admin balance adjustment"

        transaction = DBTransaction(
            user_id=user.id,
            account_id=account.id,
            transaction_type=f"admin_{op_type}",
            amount=amount,
            status="completed",
            description=reason,
            reference_number=ref_num
        )
        db.add(transaction)
        await db.flush()

        ledger_entry = DBLedger(
            user_id=user.id,
            entry_type="debit" if op_type == "debit" else "credit",
            amount=Decimal(str(round(amount, 2))),
            transaction_id=transaction.id,
            source_user_id=1 if op_type == "credit" else user.id,
            destination_user_id=user.id if op_type == "credit" else 1,
            description=reason,
            reference_number=ref_num,
            status="posted"
        )
        db.add(ledger_entry)
        await db.commit()

        return {
            "success": True,
            "message": f"Balance adjusted for {user.email}",
            "user_id": user.id,
            "amount": amount,
            "new_balance": float(account.balance)
        }

    async def get_fund_operations(self, db: AsyncSession, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get fund operation history"""
        query = select(DBTransaction).where(
            DBTransaction.transaction_type.in_(["funding", "balance_adjustment", "fund_transfer", "bulk_fund", "admin_fund", "admin_credit", "admin_debit"])
        )

        if user_id:
            query = query.where(DBTransaction.user_id == user_id)

        result = await db.execute(query.order_by(DBTransaction.created_at.desc()).limit(100))
        transactions = result.scalars().all()

        return {
            "transactions": [PydanticTransaction.model_validate(t) for t in transactions],
            "total": len(transactions)
        }

    # ==================== CARDS MANAGEMENT ====================

    async def get_user_cards_admin(self, db: AsyncSession, user_id: int) -> List[PydanticCard]:
        """Get user's cards"""
        cards = await get_user_cards(db, user_id=user_id)
        return cards

    async def create_card_for_user(self, db: AsyncSession, user_id: int, card_data: Dict[str, Any]) -> PydanticCard:
        """Create a card for user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        card_create = PydanticCard(**card_data, user_id=user_id)
        created = await create_user_card(db, card=card_create)
        return PydanticCard.model_validate(created)

    # ==================== DEPOSITS MANAGEMENT ====================

    async def get_user_deposits_admin(self, db: AsyncSession, user_id: int) -> List[PydanticDeposit]:
        """Get user's deposits"""
        deposits = await get_user_deposits(db, user_id=user_id)
        return [PydanticDeposit.model_validate(d) for d in deposits]

    async def create_deposit_for_user(self, db: AsyncSession, user_id: int, deposit_data: Dict[str, Any]) -> PydanticDeposit:
        """Create a deposit for user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        deposit_create = PydanticDeposit(**deposit_data, user_id=user_id)
        created = await create_user_deposit(db, deposit=deposit_create)
        return PydanticDeposit.model_validate(created)

    # ==================== LOANS MANAGEMENT ====================

    async def get_user_loans_admin(self, db: AsyncSession, user_id: int) -> List[PydanticLoan]:
        """Get user's loans"""
        loans = await get_user_loans(db, user_id=user_id)
        return loans

    async def create_loan_for_user(self, db: AsyncSession, user_id: int, loan_data: Dict[str, Any]) -> PydanticLoan:
        """Create a loan for user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        loan_create = PydanticLoan(**loan_data, user_id=user_id)
        created = await create_user_loan(db, loan=loan_create)
        return PydanticLoan.model_validate(created)

    # ==================== INVESTMENTS MANAGEMENT ====================

    async def get_user_investments_admin(self, db: AsyncSession, user_id: int) -> List[PydanticInvestment]:
        """Get user's investments"""
        investments = await get_user_investments(db, user_id=user_id)
        return investments

    async def create_investment_for_user(self, db: AsyncSession, user_id: int, investment_data: Dict[str, Any]) -> PydanticInvestment:
        """Create an investment for user"""
        user = await get_user(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        investment_create = PydanticInvestment(**investment_data, user_id=user_id)
        created = await create_user_investment(db, investment=investment_create)
        return PydanticInvestment.model_validate(created)

    # ==================== REPORTS ====================

    async def get_admin_reports(self, db: AsyncSession) -> Dict[str, Any]:
        """Generate admin reports"""
        users = await get_users(db, skip=0, limit=1000)
        transactions = await get_transactions(db, skip=0, limit=1000)
        kyc_submissions = await get_kyc_submissions(db)

        return {
            "users": {
                "total": len(users),
                "active": len([u for u in users if u.is_active]),
                "admin": len([u for u in users if u.is_admin])
            },
            "transactions": {
                "total": len(transactions),
                "by_status": {
                    "completed": len([t for t in transactions if t.status == "completed"]),
                    "pending": len([t for t in transactions if t.status == "pending"]),
                    "failed": len([t for t in transactions if t.status == "failed"])
                }
            },
            "kyc": {
                "total": len(kyc_submissions),
                "by_status": {
                    "pending": len([k for k in kyc_submissions if k.status == "pending"]),
                    "approved": len([k for k in kyc_submissions if k.status == "approved"]),
                    "rejected": len([k for k in kyc_submissions if k.status == "rejected"])
                }
            }
        }

    async def get_system_health(self, db: AsyncSession) -> Dict[str, Any]:
        """Get system health status"""
        try:
            result = await db.execute(select(func.count(DBUser.id)))
            user_count = result.scalar()

            return {
                "status": "healthy",
                "database": "connected",
                "users_count": user_count,
                "environment": settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "production"
            }
        except Exception as e:
            log.error(f"System health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }


# Export singleton instance
admin_service = AdminService()
