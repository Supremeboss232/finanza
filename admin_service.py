"""
Admin Service Module
Centralizes all admin operations and data handling without JSON dependencies.
Provides pure Python functions for all admin tasks.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from models import (
    User as DBUser, 
    Transaction as DBTransaction, 
    FormSubmission as DBFormSubmission,
    KYCSubmission as DBKYCSubmission,
    Card as DBCard,
    Deposit as DBDeposit,
    Loan as DBLoan,
    Investment as DBInvestment,
    Account as DBAccount,
    Ledger as DBLedger
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
        Retrieve all users with accurate balance information from ledger.
        
        RULE: Admin balances are calculated from ledger_entries (source of truth).
        This ensures consistency with user dashboard calculations.
        """
        users = await get_users(db, skip=skip, limit=limit)
        result = []
        
        # Pre-fetch all balances to prevent N+1 queries
        balance_cache = {}
        for user in users:
            balance_cache[user.id] = await BalanceServiceLedger.get_user_balance(db, user.id)
        
        for user in users:
            user_dict = PydanticUser.model_validate(user).model_dump()
            
            # Use ledger-based balance (from cache)
            user_dict['balance'] = balance_cache[user.id]
            
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
                # Hash the password and set it to hashed_password attribute
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
        """
        Retrieve all transactions with proper user details.
        
        For admin dashboard:
        - If status_filter is None: Admin sees ALL transaction statuses
        - If status_filter is 'completed': Show only completed transactions
        - If status_filter is 'pending_or_blocked': Show pending + blocked (held funds)
        
        KYC Status is read from DBKYCSubmission (source of truth), not user table.
        """
        from sqlalchemy import or_
        
        # Build query based on filter
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
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        output = []
        for t in transactions:
            try:
                tx_data = PydanticTransaction.model_validate(t)
                
                # Get user email
                user = await get_user(db, user_id=t.user_id) if t.user_id else None
                user_email = user.email if user else "N/A"
                
                # Get KYC status from source of truth (DBKYCSubmission)
                kyc_status = "not_submitted"
                if user:
                    kyc_result = await db.execute(
                        select(DBKYCSubmission).where(
                            DBKYCSubmission.user_id == user.id
                        ).order_by(DBKYCSubmission.submitted_at.desc())
                    )
                    kyc_sub = kyc_result.scalars().first()
                    if kyc_sub:
                        kyc_status = kyc_sub.status
                
                # Convert to dict and add user info
                tx_dict = tx_data.model_dump()
                tx_dict['user'] = {'email': user_email}
                tx_dict['status_label'] = self._get_status_label(t.status)
                tx_dict['kyc_status_at_time'] = kyc_status
                output.append(tx_dict)
            except Exception:
                # If validation fails, create a dict with available fields
                user = await get_user(db, user_id=t.user_id) if t.user_id else None
                user_email = user.email if user else "N/A"
                
                # Get KYC status from source of truth
                kyc_status = "not_submitted"
                if user:
                    kyc_result = await db.execute(
                        select(DBKYCSubmission).where(
                            DBKYCSubmission.user_id == user.id
                        ).order_by(DBKYCSubmission.submitted_at.desc())
                    )
                    kyc_sub = kyc_result.scalars().first()
                    if kyc_sub:
                        kyc_status = kyc_sub.status
                
                data = {
                    'id': t.id,
                    'user_id': t.user_id,
                    'account_id': t.account_id,
                    'amount': t.amount,
                    'transaction_type': t.transaction_type,
                    'status': t.status,
                    'status_label': self._get_status_label(t.status),
                    'description': getattr(t, 'description', None),
                    'reference_number': getattr(t, 'reference_number', None),
                    'created_at': t.created_at,
                    'kyc_status_at_time': kyc_status,
                    'user': {'email': user_email}
                }
                output.append(data)
        
        return output
    
    @staticmethod
    def _get_status_label(status: str) -> str:
        """Get user-friendly label for transaction status"""
        labels = {
            'completed': '✓ Completed',
            'pending': '⏳ Pending',
            'blocked': '🚫 Blocked',
            'failed': '❌ Failed',
            'cancelled': '◀ Cancelled'
        }
        return labels.get(status, status)
    
    async def get_recent_transactions(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent transactions with proper user/account linking and system transaction labeling.
        
        RULE: Join ledger → accounts → users to get complete transaction context.
        System/admin transactions show 'SYSTEM' or 'ADMIN' as user label.
        """
        from sqlalchemy import join, and_
        from models import Ledger as DBLedger, Account as DBAccount
        
        # Query ledger entries with user/account info
        query = select(
            DBLedger.id,
            DBLedger.user_id,
            DBLedger.amount,
            DBLedger.entry_type,
            DBLedger.description,
            DBLedger.status,
            DBLedger.created_at,
            DBUser.email,
            DBAccount.account_number,
            DBLedger.source_user_id,
            DBLedger.destination_user_id
        ).select_from(
            DBLedger
        ).outerjoin(
            DBUser, DBLedger.user_id == DBUser.id
        ).outerjoin(
            DBAccount, DBAccount.owner_id == DBLedger.user_id
        ).order_by(
            DBLedger.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        transactions = []
        for row in rows:
            ledger_id, user_id, amount, entry_type, description, status, created_at, email, account_num, source_user_id, dest_user_id = row
            
            # Determine user label (handle system/admin transactions)
            if user_id == 1 or email is None:
                # System account
                user_label = "SYSTEM"
            elif source_user_id == 1:
                # Incoming from system
                user_label = f"{email}" if email else "SYSTEM"
            elif dest_user_id == 1:
                # Outgoing to system
                user_label = f"{email}" if email else "SYSTEM"
            else:
                user_label = email or "N/A"
            
            tx_dict = {
                'id': ledger_id,
                'user_id': user_id,
                'user_email': user_label,
                'amount': float(amount),
                'type': entry_type.upper(),
                'description': description,
                'status': status,
                'account_number': account_num or "N/A",
                'created_at': created_at.isoformat() if created_at else None
            }
            transactions.append(tx_dict)
        
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
    
    async def approve_kyc(self, db: AsyncSession, submission_id: int) -> Dict[str, str]:
        """Approve a KYC submission"""
        result = await approve_kyc_submission(db, submission_id=submission_id)
        if not result:
            raise ValueError(f"KYC submission {submission_id} not found")
        return {"message": f"KYC submission {submission_id} approved"}
    
    async def reject_kyc(self, db: AsyncSession, submission_id: int, reason: str = "") -> Dict[str, str]:
        """Reject a KYC submission"""
        result = await reject_kyc_submission(db, submission_id=submission_id, rejection_reason=reason)
        if not result:
            raise ValueError(f"KYC submission {submission_id} not found")
        return {"message": f"KYC submission {submission_id} rejected"}
    
    # ==================== DASHBOARD METRICS ====================
    
    async def get_dashboard_metrics(self, db: AsyncSession) -> AdminDashboardMetrics:
        """
        Get dashboard metrics using LEDGER-BASED calculations (source of truth).
        
        RULE: All admin metrics are derived from ledger_entries.
        - Total Deposits = sum of all credits from system account
        - Total Volume = sum of all credits (all users)
        - Active Users = count of distinct users with ledger entries
        - Total User Balances = sum of (credits - debits) for all users
        
        This ensures consistency with user dashboard calculations.
        """
        try:
            # 1. Count of distinct users with ledger activity
            ledger_users_result = await db.execute(
                select(func.count(distinct(DBLedger.user_id))).where(
                    DBLedger.status == "posted"
                )
            )
            active_users = ledger_users_result.scalar() or 0
            
            # 2. Total deposits from system (sum of credits from system account user_id=1)
            total_deposits = await BalanceServiceLedger.get_admin_total_deposits(db)
            
            # 3. Total volume (sum of all credits across all users)
            total_volume = await BalanceServiceLedger.get_admin_total_volume(db)
            
            # 4. Count pending KYC submissions
            pending_kyc_count = await db.scalar(
                select(func.count(DBKYCSubmission.id)).where(
                    DBKYCSubmission.status == "pending"
                )
            )
            
            # 5. Total ledger entries (number of transactions)
            transaction_count = await db.scalar(
                select(func.count(DBLedger.id)).where(
                    DBLedger.status == "posted"
                )
            )
            
            # 6. Recent users
            recent_users_result = await db.execute(
                select(DBUser).order_by(DBUser.created_at.desc()).limit(5)
            )
            recent_users = [PydanticUser.model_validate(u) for u in recent_users_result.scalars()]
            
            # 7. Recent transactions from ledger (properly joined with user data)
            recent_tx_list = await self.get_recent_transactions(db, limit=5)
            
            return AdminDashboardMetrics(
                total_users=active_users,
                pending_kyc=pending_kyc_count or 0,
                total_transactions=transaction_count or 0,
                total_deposits=total_deposits,
                total_volume=total_volume,
                recent_users=recent_users,
                recent_transactions=recent_tx_list
            )
        except Exception as e:
            log.error(f"Error calculating dashboard metrics: {e}")
            raise
    
    # ==================== FORM SUBMISSIONS ====================
    
    async def get_top_users_by_balance(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users ranked by ledger-based balance.
        
        RULE: Ranking is calculated from ledger_entries (source of truth).
        This ensures consistency with user dashboard balance display.
        """
        # Get all users
        all_users_result = await db.execute(select(DBUser))
        all_users = all_users_result.scalars().all()
        
        # Calculate balance for each user and build list
        user_balances = []
        for user in all_users:
            balance = await BalanceServiceLedger.get_user_balance(db, user.id)
            if balance > 0:  # Only include users with positive balance
                user_balances.append({
                    'rank': 0,  # Will set after sorting
                    'user_id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'balance': balance,
                    'status': 'Active' if user.is_active else 'Inactive'
                })
        
        # Sort by balance (descending)
        user_balances.sort(key=lambda x: x['balance'], reverse=True)
        
        # Set ranks and limit
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
        """
        Fund a user account from System Reserve Account (Admin operation).
        
        ⚠️ ADMIN-ONLY OPERATION
        
        Uses SystemFundService to:
        1. Create double-entry ledger (debit system, credit user)
        2. Create transaction record
        3. Update account balance atomically
        4. Log audit trail
        
        Source: System Reserve Account (SYS-RESERVE-0001)
        Destination: Target user's account
        
        Returns: Comprehensive response with ledger IDs
        """
        from transaction_validator import TransactionValidator
        from transaction_gate import TransactionGate
        from sqlalchemy import select
        
        try:
            # Find user by email
            user = await get_user_by_email(db, email=fund_request.email)
            if not user:
                raise ValueError(f"User with email {fund_request.email} not found")
            
            # Validate the funding request
            is_valid, reason = await TransactionValidator.validate_deposit(
                db=db,
                user_id=user.id,
                amount=fund_request.amount,
                account_id=None
            )
            
            if not is_valid:
                raise ValueError(f"Validation failed: {reason}")
            
            # Get user account (we know it exists from validation)
            account_result = await db.execute(
                select(DBAccount).filter(DBAccount.owner_id == user.id)
            )
            account = account_result.scalars().first()
            
            # Use TransactionGate to determine final status (RULE 2: No KYC, no completed)
            can_complete, intended_status, gate_reason = await TransactionGate.validate_deposit(
                db=db,
                user_id=user.id,
                amount=fund_request.amount,
                account_id=account.id
            )
            
            # Use SystemFundService to perform fund transfer
            # This creates ledger entries, transaction, and audit log
            result = await SystemFundService.fund_user_from_system(
                db=db,
                target_user_id=user.id,
                target_account_id=account.id,
                amount=fund_request.amount,
                admin_user_id=admin_user_id,
                reason=fund_request.notes or f"Admin funding from {fund_request.fund_source}"
            )
            
            if not result["success"]:
                raise ValueError(f"Fund transfer failed: {result.get('error')}")
            
            return FundUserResponse(
                success=True,
                message=f"Successfully funded {user.email} with ${fund_request.amount:,.2f}. "
                        f"Ledger entries created (Debit: {result['debit_entry_id']}, Credit: {result['credit_entry_id']})",
                transaction_id=result["transaction_id"],
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
        """Adjust user balance"""
        user = await get_user_by_email(db, email=adjust_request.email)
        if not user:
            raise ValueError(f"User with email {adjust_request.email} not found")
        
        # Create adjustment transaction
        transaction = DBTransaction(
            user_id=user.id,
            transaction_type="balance_adjustment",
            amount=adjust_request.amount,
            status="completed",
            description=adjust_request.reason or "Admin balance adjustment"
        )
        
        db.add(transaction)
        await db.commit()
        
        return {
            "success": True,
            "message": f"Balance adjusted for {user.email}",
            "user_id": user.id,
            "amount": adjust_request.amount
        }
    
    async def get_fund_operations(self, db: AsyncSession, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get fund operation history"""
        query = select(DBTransaction).where(DBTransaction.transaction_type.in_(["funding", "balance_adjustment", "fund_transfer", "bulk_fund"]))
        
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
        
        # Calculate statistics
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
            # Test database connection
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
