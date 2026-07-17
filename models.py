# models.py
# SQLAlchemy models defining database tables (User, Admin, Transactions, KYC, etc.).

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date, ForeignKey, Float, Numeric, Text, Index, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base # Assuming database.py defines Base
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    account_number = Column(String, unique=True, index=True, nullable=True)
    account_type = Column(String, default="Checking", nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    admin_role = Column(String, default="STANDARD", nullable=False)  # STANDARD, ADMIN, TREASURY, SUPER_ADMIN
    # ⚠️ RULE 1: KYC Status controls transaction completion
    # STATES: not_started, pending, approved, rejected
    # Only 'approved' KYC allows completed transactions
    kyc_status = Column(String, default="not_started", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Admin display fields
    address = Column(String, nullable=True)
    region = Column(String, nullable=True)
    routing_number = Column(String, nullable=True)
    
    # MFA/2FA Fields
    mfa_secret = Column(String, nullable=True)  # Base32 encoded TOTP secret
    mfa_enabled = Column(Boolean, default=False)  # Whether MFA is enabled
    mfa_backup_codes = Column(Text, nullable=True)  # Comma-separated hashed backup codes
    mfa_enabled_at = Column(DateTime(timezone=True), nullable=True)  # When MFA was enabled
    
    # Account Status Flags
    is_suspended = Column(Boolean, default=False)  # Admin suspended this user - cannot login
    is_frozen = Column(Boolean, default=False)  # Admin froze account - cannot do any operations
    
    # Granular Permissions
    custom_permissions = Column(Text, nullable=True)  # JSON: {granted: [...], denied: [...]}

    # Relationships
    accounts = relationship("Account", back_populates="owner")
    transactions = relationship(
        "Transaction",
        back_populates="user",
        foreign_keys="[Transaction.user_id]",
    )
    kyc_info = relationship("KYCInfo", uselist=False, back_populates="user")
    investments = relationship("Investment", back_populates="owner")
    loans = relationship("Loan", back_populates="owner")
    cards = relationship("Card", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")
    goals = relationship("Goal", back_populates="owner")
    notifications = relationship("Notification", back_populates="recipient")
    support_tickets = relationship("SupportTicket", back_populates="submitter")
    user_settings = relationship("UserSettings", uselist=False, back_populates="user")
    projects = relationship("Project", back_populates="owner")
    mobile_deposits = relationship("MobileDeposit", foreign_keys="MobileDeposit.user_id", back_populates="user")

    @property
    def balance(self):
        if 'accounts' in self.__dict__ and self.accounts:
            return sum(acc.balance for acc in self.accounts)
        return 0.0

    @balance.setter
    def balance(self, value):
        if 'accounts' in self.__dict__ and self.accounts:
            self.accounts[0].balance = value


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, comment="Account ID - unique, immutable")
    account_number = Column(String, unique=True, index=True, nullable=False, comment="User-facing account number - immutable")
    account_type = Column(String, default="savings", nullable=False)  # savings, checking, business, investment, loan
    balance = Column(Numeric(15, 2), default=0.0, nullable=False)  # Source of truth: synced from ledger (Numeric for precision)
    currency = Column(String, default="USD", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="User ID - Foreign Key (NOT for admin accounts)")  # REQUIRED: Every account must have an owner
    
    # Region association for multi-region support
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True, index=True, comment="Region where account is domiciled")
    
    # Account status: active, frozen, closed
    status = Column(String, default="active", nullable=False)
    
    # KYC level required for this account: none, basic, full
    kyc_level = Column(String, default="basic", nullable=False)
    
    # Flag to exclude from user-account binding enforcement (for admin/system accounts)
    is_admin_account = Column(Boolean, default=False, nullable=False, comment="If True, not subject to user binding enforcement")
    
    # Flag for system/treasury accounts
    is_system_account = Column(Boolean, default=False, nullable=False, comment="If True, only allows admin disbursements")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    region = relationship("Region", back_populates="accounts")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # REQUIRED: Every transaction must belong to a user
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)  # REQUIRED: Every transaction must belong to an account
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional recipient for payment flows
    amount = Column(Numeric(15, 2), nullable=False)  # Numeric for financial precision
    transaction_type = Column(String, nullable=False)  # e.g., "deposit", "withdrawal", "transfer", "fund_transfer"
    direction = Column(String, nullable=True)  # "credit" or "debit" for clarity
    status = Column(String, default="pending", nullable=False)  # STATES: pending, blocked, completed, failed, cancelled
    # ⚠️ CRITICAL RULE: Only 'completed' transactions affect balance
    # 'blocked' and 'pending' are held funds (visible to admin, not to user balance)
    description = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    # ⚠️ RULE 2: Transaction must not complete if KYC not approved
    kyc_status_at_time = Column(String, nullable=True)  # snapshot of kyc_status when created
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship(
        "User",
        back_populates="transactions",
        foreign_keys=[user_id],
    )
    recipient = relationship(
        "User",
        foreign_keys=[recipient_user_id],
    )
    account = relationship("Account", back_populates="transactions")

class KYCInfo(Base):
    __tablename__ = "kyc_info"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    email = Column(String, nullable=True)  # Email from KYC form submission
    document_type = Column(String) # e.g., "passport", "driver_license"
    document_number = Column(String)
    status = Column(String, default="pending") # e.g., "pending", "approved", "rejected"
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Document Upload Tracking (True when document successfully uploaded and stored)
    id_front_uploaded = Column(Boolean, default=False)
    id_back_uploaded = Column(Boolean, default=False)
    ssn_uploaded = Column(Boolean, default=False)
    proof_of_address_uploaded = Column(Boolean, default=False)
    id_front_path = Column(String, nullable=True)
    id_back_path = Column(String, nullable=True)
    ssn_path = Column(String, nullable=True)
    proof_of_address_path = Column(String, nullable=True)
    
    # Document Expiry & Validation
    id_expiry_date = Column(DateTime(timezone=True), nullable=True)
    proof_of_address_date = Column(DateTime(timezone=True), nullable=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    
    # KYC Status Workflow
    # not_started -> pending_documents -> submitted -> pending_review -> approved/rejected
    kyc_status = Column(String, default="not_started", nullable=False)
    rejection_reason = Column(String, nullable=True)
    
    # Submission Lock - prevents further edits after user submits
    kyc_submitted = Column(Boolean, default=False, nullable=False)
    submission_locked = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    documents_submitted_at = Column(DateTime(timezone=True), nullable=True)
    submission_timestamp = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="kyc_info")


class KYCSubmission(Base):
    __tablename__ = "kyc_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    document_type = Column(String)
    document_file_path = Column(String)
    status = Column(String, default="pending")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")

class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    form_type = Column(String, index=True) # e.g., "contact", "support_ticket"
    data = Column(String) # Could be JSON/Text depending on DB
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    submitter = relationship("User")

class Deposit(Base):
    __tablename__ = "deposits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(15, 2))  # Numeric for financial precision
    current_balance = Column(Numeric(15, 2))  # Numeric for financial precision
    currency = Column(String, default="USD")
    interest_rate = Column(Numeric(5, 4), default=0.0)  # Numeric for rate precision (e.g., 5.2500%)
    term_months = Column(Integer, default=12)
    maturity_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User")

class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    loan_type = Column(String, nullable=True)  # personal, auto, home, student, business
    amount = Column(Numeric(15, 2))  # Numeric for financial precision
    remaining_balance = Column(Numeric(15, 2))  # Numeric for financial precision
    monthly_payment = Column(Numeric(15, 2), default=0.0)  # Numeric for financial precision
    paid_amount = Column(Numeric(15, 2), default=0.0)  # Numeric for financial precision
    interest_rate = Column(Numeric(5, 4))  # Numeric for rate precision (e.g., 5.2500%)
    term_months = Column(Integer)
    purpose = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="loans")

class Investment(Base):
    __tablename__ = "investments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    investment_type = Column(String)
    amount = Column(Numeric(15, 2))  # Numeric for financial precision
    current_value = Column(Numeric(15, 2), nullable=True)  # Numeric for financial precision
    interest_earned = Column(Numeric(15, 2), default=0.0)  # Numeric for financial precision
    annual_return_rate = Column(Numeric(5, 4), default=0.0)  # Numeric for rate precision (e.g., 5.2500%)
    purpose = Column(String, nullable=True)
    maturity_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="investments")

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    card_number = Column(String, unique=True)
    card_type = Column(String)
    card_holder_name = Column(String, nullable=True)
    expiry_date = Column(String)
    balance = Column(Numeric(15, 2), default=0.0)  # Numeric for financial precision
    credit_limit = Column(Numeric(15, 2), default=5000.0)  # Numeric for financial precision
    transaction_limit = Column(Numeric(15, 2), default=10000.0)  # Numeric for financial precision
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="cards")

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    policy_number = Column(String, unique=True, index=True)
    policy_type = Column(String)  # e.g., "health", "auto", "home", "life"
    coverage_amount = Column(Numeric(15, 2))  # Numeric for financial precision
    premium = Column(Numeric(12, 2))  # Numeric for financial precision
    start_date = Column(DateTime(timezone=True))
    renewal_date = Column(DateTime(timezone=True))
    status = Column(String, default="active")  # e.g., "active", "expired", "cancelled"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User")
    claims = relationship("Claim", back_populates="policy")

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"))
    claim_number = Column(String, unique=True, index=True)
    amount = Column(Numeric(15, 2))  # Numeric for financial precision
    status = Column(String, default="pending")  # e.g., "pending", "approved", "rejected", "paid"
    description = Column(String)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    policy = relationship("Policy", back_populates="claims")

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String)  # e.g., "groceries", "utilities", "entertainment"
    limit = Column(Numeric(12, 2))  # Numeric for financial precision
    spent = Column(Numeric(12, 2), default=0.0)  # Numeric for financial precision
    month = Column(String)  # e.g., "2025-01" for January 2025
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal_name = Column(String)
    target_amount = Column(Numeric(12, 2))  # Numeric for financial precision
    current_amount = Column(Numeric(12, 2), default=0.0)  # Numeric for financial precision
    deadline = Column(DateTime(timezone=True))
    status = Column(String, default="active")  # e.g., "active", "completed", "abandoned"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(String)
    notification_type = Column(String)  # e.g., "transaction", "alert", "reminder", "kyc"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    recipient = relationship("User")

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject = Column(String)
    message = Column(String)
    status = Column(String, default="open")  # e.g., "open", "in_progress", "resolved", "closed"
    priority = Column(String, default="normal")  # e.g., "low", "normal", "high", "urgent"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    submitter = relationship("User")

class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    two_factor_enabled = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    preferences = Column(String, nullable=True)  # JSON string for flexible preferences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="user_settings")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_name = Column(String)
    description = Column(String)
    status = Column(String, default="planning")  # e.g., "planning", "in_progress", "completed"
    budget = Column(Numeric(12, 2), nullable=True)  # Numeric for financial precision
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User")


# ===== LEDGER MODEL: Double-Entry Accounting System =====
# This is the SOURCE OF TRUTH for all money movements.
# Every financial transaction creates TWO ledger entries (debit and credit).
# Balance = sum(credits) - sum(debits) for each user

class Ledger(Base):
    """
    Double-entry ledger for financial accounting.
    
    PRINCIPLE: Every money movement is atomic.
    
    A fund transfer creates TWO entries:
    1. Debit entry: Money leaves sender (credit_user_id)
    2. Credit entry: Money enters receiver (user_id)
    
    Balance for user = sum(credits to user) - sum(debits from user)
    
    System/Admin account has user_id = 1 (reserved)
    """
    __tablename__ = "ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Core fields: who does the entry belong to
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Primary account owner
    
    # Entry type: DEBIT or CREDIT
    entry_type = Column(String, nullable=False)  # "debit" or "credit"
    
    # Amount: always positive, direction determined by entry_type
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Transaction linkage
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    
    # Double-entry linkage: related entry (the matching pair)
    related_entry_id = Column(Integer, ForeignKey("ledger.id"), nullable=True)
    
    # Money source/destination (for audit)
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # If money came from another user
    destination_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # If money went to another user
    
    # Description of what happened
    description = Column(String, nullable=False)
    reference_number = Column(String, nullable=True, index=True)  # External reference (e.g., check #, wire #)
    
    # Status tracking
    status = Column(String, default="posted", nullable=False)  # "pending", "posted", "reversed"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    user = relationship("User", foreign_keys=[user_id])
    source_user = relationship("User", foreign_keys=[source_user_id])
    destination_user = relationship("User", foreign_keys=[destination_user_id])
    
    def __repr__(self):
        return f"<Ledger {self.entry_type.upper()} ${self.amount} to User {self.user_id}>"


class AuditLog(Base):
    """
    Immutable audit trail for all admin actions.
    
    RULE: Every admin action must create an AuditLog entry.
    - Admin ID: who performed the action
    - User ID: who the action was performed on
    - Account ID: which account was affected
    - Action type: fund, freeze, unfreeze, reverse_transaction, approve_kyc, reject_kyc, reset_password, etc.
    - Timestamp: when it happened
    - Reason: why it happened (admin notes)
    - Details: JSON data for specific action details
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who performed the action
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Who the action was performed on
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Which account was affected (optional but recommended)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    
    # What action was performed
    # Values: "fund", "freeze", "unfreeze", "reverse_transaction", "approve_kyc", "reject_kyc", 
    #         "reset_password", "create_user", "update_user", "delete_user", "set_admin", etc.
    action_type = Column(String, nullable=False, index=True)
    
    # Why it happened (admin notes)
    reason = Column(String, nullable=True)
    
    # Detailed data (as JSON-like dict)
    details = Column(String, nullable=True)  # Store as stringified JSON
    
    # Result of the action
    status = Column(String, default="success", nullable=False)  # "success", "failed", "pending"
    status_message = Column(String, nullable=True)
    
    # Audit immutability
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    
    # Relationships
    admin = relationship("User", foreign_keys=[admin_id])
    account_rel = relationship("Account", foreign_keys=[account_id])
    
    def __repr__(self):
        return f"<AuditLog {self.action_type} by Admin {self.admin_id} on User {self.user_id} at {self.created_at}>"


# Add minimal Admin model for backward compatibility
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    role = Column(String, default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Minimal placeholder models for references in Account
class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False)  # e.g., "US", "EU", "APAC"
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship: accounts in this region
    accounts = relationship("Account", back_populates="region")

# Stub models for any other missing dependencies (common in large projects)
class FundSource(Base):
    __tablename__ = "fund_sources"
    id = Column(Integer, primary_key=True, index=True)

class AccountTier(Base):
    __tablename__ = "account_tiers"
    id = Column(Integer, primary_key=True, index=True)

class AMLAlert(Base):
    __tablename__ = "aml_alerts"
    id = Column(Integer, primary_key=True, index=True)

class ComplianceReport(Base):
    __tablename__ = "compliance_reports"
    id = Column(Integer, primary_key=True, index=True)

class CountryRiskAssessment(Base):
    __tablename__ = "country_risk_assessments"
    id = Column(Integer, primary_key=True, index=True)

class FlaggedTransaction(Base):
    __tablename__ = "flagged_transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String, default="pending", nullable=True)
    risk_level = Column(String, default="medium", nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

class FundTransfer(Base):
    __tablename__ = "fund_transfers"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=True)  # Numeric for financial precision
    status = Column(String, default="pending", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    id = Column(Integer, primary_key=True, index=True)

class MobileDeposit(Base):
    __tablename__ = "mobile_deposits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    check_number = Column(String, nullable=True)
    issuer_name = Column(String, nullable=True)
    bank_routing = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    status = Column(String, default="pending_images", nullable=False, index=True)
    quality_score = Column(Integer, nullable=True)
    front_image_url = Column(String(2048), nullable=True)
    back_image_url = Column(String(2048), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="mobile_deposits")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    account = relationship("Account", foreign_keys=[account_id])

class SanctionsScreening(Base):
    __tablename__ = "sanctions_screenings"
    id = Column(Integer, primary_key=True, index=True)

class ScheduledTransfer(Base):
    __tablename__ = "scheduled_transfers"
    id = Column(Integer, primary_key=True, index=True)

class ScheduledTransferExecution(Base):
    __tablename__ = "scheduled_transfer_executions"
    id = Column(Integer, primary_key=True, index=True)

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True, index=True)

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id = Column(Integer, primary_key=True, index=True)


# ===== CREDIT & ACCOUNT MANAGEMENT MODELS =====

class CreditScore(Base):
    """Credit score information"""
    __tablename__ = "credit_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    score_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class RegionCompliance(Base):
    """Regional compliance requirements and settings"""
    __tablename__ = "region_compliance"
    
    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String, nullable=False, unique=True, index=True)
    country_code = Column(String, nullable=True)
    kyc_required = Column(Boolean, default=True)
    aml_level = Column(String, default="standard")  # standard, enhanced, high_risk
    transaction_limit = Column(Numeric(15, 2), default=50000.0)  # Numeric for financial precision
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AccountHold(Base):
    """Account hold/freeze records"""
    __tablename__ = "account_holds"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True), nullable=True)
    
    account = relationship("Account")


class LoanPayment(Base):
    """Loan payment records"""
    __tablename__ = "loan_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="completed", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class TransactionHistory(Base):
    """Transaction history archive"""
    __tablename__ = "transaction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")
    user = relationship("User")
    account = relationship("Account")


class Statement(Base):
    """Account statement"""
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    statement_date = Column(DateTime(timezone=True), server_default=func.now())
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    beginning_balance = Column(Numeric(12, 2), nullable=False)
    ending_balance = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account")


class Delinquency(Base):
    """Loan delinquency record"""
    __tablename__ = "delinquencies"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    days_overdue = Column(Integer, default=0)
    status = Column(String, default="current", nullable=False)  # current, 30, 60, 90+
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    loan = relationship("Loan")


class LoanHistory(Base):
    """Loan change history / audit trail"""
    __tablename__ = "loan_history"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    change_type = Column(String, nullable=False)  # created, modified, paid, defaulted, etc.
    amount = Column(Numeric(12, 2), nullable=True)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class LoanModification(Base):
    """Loan modification requests and approvals"""
    __tablename__ = "loan_modifications"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    modification_type = Column(String, nullable=False)  # rate_reduction, term_extension, forbearance
    requested_amount = Column(Numeric(12, 2), nullable=True)
    approved_amount = Column(Numeric(12, 2), nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, approved, denied
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    loan = relationship("Loan")


class LoanCollection(Base):
    """Loan collection activities"""
    __tablename__ = "loan_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    collection_date = Column(DateTime(timezone=True), server_default=func.now())
    attempt_type = Column(String, nullable=False)  # phone_call, letter, legal_action
    status = Column(String, default="pending", nullable=False)  # pending, successful, failed
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class Forbearance(Base):
    """Loan forbearance records"""
    __tablename__ = "forbearances"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    forbearance_type = Column(String, nullable=False)  # payment_pause, reduced_payment, interest_only
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    monthly_payment_amount = Column(Numeric(12, 2), nullable=True)
    status = Column(String, default="active", nullable=False)  # active, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class ChargeOff(Base):
    """Charge-off records for defaulted loans"""
    __tablename__ = "charge_offs"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    charged_off_date = Column(DateTime(timezone=True), server_default=func.now())
    charged_off_amount = Column(Numeric(12, 2), nullable=False)
    recovery_status = Column(String, default="uncollected", nullable=False)  # uncollected, partial, recovered
    recovery_amount = Column(Numeric(12, 2), default=0.0)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class LoanPaymentSchedule(Base):
    """Payment schedule for loans"""
    __tablename__ = "loan_payment_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    scheduled_amount = Column(Numeric(12, 2), nullable=False)
    principal_amount = Column(Numeric(12, 2), nullable=False)
    interest_amount = Column(Numeric(12, 2), nullable=False)
    payment_status = Column(String, default="pending", nullable=False)  # pending, paid, partial, missed
    paid_amount = Column(Numeric(12, 2), default=0.0)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class Prepayment(Base):
    """Prepayment records"""
    __tablename__ = "prepayments"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    prepayment_date = Column(DateTime(timezone=True), server_default=func.now())
    amount = Column(Numeric(12, 2), nullable=False)
    penalty = Column(Numeric(12, 2), default=0.0)
    net_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


class CollectionContact(Base):
    """Collection contact records"""
    __tablename__ = "collection_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False, index=True)
    contact_date = Column(DateTime(timezone=True), server_default=func.now())
    contact_method = Column(String, nullable=False)  # phone, email, letter, in_person
    contact_status = Column(String, nullable=False)  # successful, voicemail, no_answer
    notes = Column(String, nullable=True)
    promised_payment_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    loan = relationship("Loan")


# ===== PAYMENT RETURNS & ACH MODELS =====

class ACHReturn(Base):
    """ACH return record"""
    __tablename__ = "ach_returns"
    
    id = Column(Integer, primary_key=True, index=True)
    ach_entry_id = Column(Integer, ForeignKey("ach_entries.id"), nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    return_code = Column(String, nullable=False)  # R01, R02, R03, etc.
    return_reason = Column(String, nullable=False)
    return_date = Column(DateTime(timezone=True), server_default=func.now())
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, default="received", nullable=False)  # received, processed, corrected
    correction_entry_id = Column(Integer, ForeignKey("ach_entries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


class NSFManagement(Base):
    """NSF (Non-Sufficient Funds) management"""
    __tablename__ = "nsf_management"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, index=True)
    insufficient_amount = Column(Numeric(12, 2), nullable=False)
    nsf_fee = Column(Numeric(10, 2), default=0.0)
    fee_applied_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending", nullable=False)  # pending, charged, waived, reversed
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account")
    transaction = relationship("Transaction")


class PaymentException(Base):
    """Payment exception records"""
    __tablename__ = "payment_exceptions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    exception_type = Column(String, nullable=False)  # timeout, invalid_account, insufficient_funds
    exception_code = Column(String, nullable=False)
    message = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, resolved, escalated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    transaction = relationship("Transaction")


class TransactionDispute(Base):
    """Transaction dispute/chargeback records"""
    __tablename__ = "transaction_disputes"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dispute_reason = Column(String, nullable=False)
    dispute_amount = Column(Numeric(12, 2), nullable=False)
    dispute_status = Column(String, default="open", nullable=False)  # open, investigating, resolved, denied
    filed_date = Column(DateTime(timezone=True), server_default=func.now())
    resolved_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")
    user = relationship("User")


class ReturnProcessing(Base):
    """Return processing workflow tracking"""
    __tablename__ = "return_processing"
    
    id = Column(Integer, primary_key=True, index=True)
    return_type = Column(String, nullable=False)  # ach_return, nsf_return, chargeback
    reference_id = Column(Integer, nullable=False, index=True)
    status = Column(String, default="received", nullable=False)  # received, processing, completed, failed
    amount = Column(Numeric(12, 2), nullable=False)
    return_code = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    received_date = Column(DateTime(timezone=True), server_default=func.now())
    processed_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===== COMPLIANCE & REGULATORY MODELS =====

class HMDAApplication(Base):
    """HMDA (Home Mortgage Disclosure Act) application data"""
    __tablename__ = "hmda_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True, index=True)
    applicant_name = Column(String, nullable=False)
    loan_amount = Column(Numeric(12, 2), nullable=False)
    property_address = Column(String, nullable=True)
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    loan_purpose = Column(String, nullable=True)  # purchase, refinance, improvement
    fair_lending_flagged = Column(Boolean, default=False)
    action_taken = Column(String, nullable=True)  # approved, denied, withdrawn
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HMDAApplicant(Base):
    """HMDA applicant demographic information"""
    __tablename__ = "hmda_applicants"
    
    id = Column(Integer, primary_key=True, index=True)
    hmda_application_id = Column(Integer, ForeignKey("hmda_applications.id"), nullable=False)
    applicant_type = Column(String, nullable=False)  # primary, co-applicant
    ethnicity = Column(String, nullable=True)
    race = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    income = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FairLendingCheck(Base):
    """Fair Lending compliance check"""
    __tablename__ = "fair_lending_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    hmda_application_id = Column(Integer, ForeignKey("hmda_applications.id"), nullable=False)
    check_date = Column(DateTime(timezone=True), server_default=func.now())
    check_type = Column(String, nullable=False)  # rate_comparison, approval_rate, pricing
    result = Column(String, nullable=False)  # pass, fail, review_required
    details = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HMDASubmission(Base):
    """HMDA data submission records"""
    __tablename__ = "hmda_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_year = Column(Integer, nullable=False)
    submission_date = Column(DateTime(timezone=True), server_default=func.now())
    record_count = Column(Integer, default=0)
    status = Column(String, default="draft", nullable=False)  # draft, submitted, accepted, rejected
    filing_institution_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterestAccrual(Base):
    """Interest accrual tracking"""
    __tablename__ = "interest_accruals"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    accrual_date = Column(DateTime(timezone=True), server_default=func.now())
    amount = Column(Numeric(12, 2), nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)  # Numeric for rate precision (e.g., 5.2500%)
    posted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account")


class SweepRule(Base):
    """Automatic sweep rules"""
    __tablename__ = "sweep_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    source_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    sweep_type = Column(String, nullable=False)  # threshold, daily, weekly, monthly
    threshold_amount = Column(Numeric(12, 2), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account", foreign_keys=[account_id])
    source_account = relationship("Account", foreign_keys=[source_account_id])


class AccountClosure(Base):
    """Account closure records"""
    __tablename__ = "account_closures"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    closure_reason = Column(String, nullable=False)
    final_balance = Column(Numeric(12, 2), nullable=False)
    closed_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account")
    closed_by_user = relationship("User")

# ===== SETTLEMENT & PAYMENT PROCESSING MODELS =====

class Settlement(Base):
    """Settlement record for payment processing"""
    __tablename__ = "settlements"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    rail_type = Column(String, nullable=False)  # ACH, Wire, RTP, FedNow, Internal
    status = Column(String, default="pending", nullable=False)  # pending, settled, failed, reversed
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    transaction = relationship("Transaction")


class SettlementState(Base):
    """Settlement state tracking"""
    __tablename__ = "settlement_states"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    current_state = Column(String, default="initiated", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    transaction = relationship("Transaction")


class ACHFile(Base):
    """ACH batch file"""
    __tablename__ = "ach_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    entries = relationship("ACHEntry", back_populates="file")


class ACHEntry(Base):
    """ACH transaction entry"""
    __tablename__ = "ach_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("ach_files.id"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    routing_number = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    file = relationship("ACHFile", back_populates="entries")
    transaction = relationship("Transaction")


class WireTransfer(Base):
    """Wire transfer details"""
    __tablename__ = "wire_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    receiving_bank = Column(String, nullable=False)
    receiving_routing = Column(String, nullable=False)
    receiving_account = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    fee = Column(Numeric(10, 2), default=0.0)
    status = Column(String, default="pending", nullable=False)
    reference_number = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


class RTPTransaction(Base):
    """Real-Time Payment transaction"""
    __tablename__ = "rtp_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    routing_number = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


# ==================== NEW ADMIN FEATURES ====================

class ScheduledAdjustment(Base):
    """Scheduled balance adjustments - recurring or one-time"""
    __tablename__ = "scheduled_adjustments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)  # Positive for credit, negative for debit
    reason = Column(String, nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    recurrence = Column(String, default="ONCE")  # ONCE, DAILY, WEEKLY, MONTHLY, QUARTERLY
    recurrence_end = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="PENDING", nullable=False, index=True)  # PENDING, EXECUTED, FAILED, CANCELLED
    executed_at = Column(DateTime(timezone=True), nullable=True)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ApprovalRequest(Base):
    """Multi-admin approval workflow requests"""
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type = Column(String, nullable=False, index=True)  # BALANCE_ADJUSTMENT, ADMIN_CREATION, etc
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    data = Column(Text, nullable=False)  # JSON of action details
    status = Column(String, default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED, EXPIRED
    required_approvals = Column(Integer, default=2)
    current_approvals = Column(Integer, default=0)
    deadline = Column(DateTime(timezone=True), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_voted_at = Column(DateTime(timezone=True), nullable=True)


class ApprovalVote(Base):
    """Individual approval votes on approval requests"""
    __tablename__ = "approval_votes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, ForeignKey("approval_requests.id"), nullable=False, index=True)
    voted_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vote = Column(String, nullable=False)  # APPROVE or REJECT
    comments = Column(String, nullable=True)
    voted_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== NORMALIZED PERMISSION STORAGE ====================

class AdminPermissionOverride(Base):
    """Normalized storage for granular permission overrides
    
    Instead of storing JSON in User.custom_permissions, store individual rows
    This allows better querying and auditing of permission changes
    """
    __tablename__ = "admin_permission_overrides"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(String, nullable=False, index=True)  # e.g., "perm:users:suspend"
    action = Column(String, nullable=False)  # "GRANT" or "DENY"
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Which admin granted this
    reason = Column(String, nullable=True)  # Why this permission was granted/denied
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional: Permission expires
    is_active = Column(Boolean, default=True, index=True)  # Soft delete


class PermissionAuditLog(Base):
    """Audit trail of all permission changes"""
    __tablename__ = "permission_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(String, nullable=False)
    action = Column(String, nullable=False)  # GRANT, DENY, RESET
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    old_value = Column(String, nullable=True)  # Previous permission state
    new_value = Column(String, nullable=True)  # New permission state
    reason = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class RateLimitLog(Base):
    """Rate limiting audit trail (for database backend)"""
    __tablename__ = "rate_limit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String, nullable=False, index=True)  # user_id or IP address
    identifier_type = Column(String, nullable=False)  # "user" or "ip"
    endpoint = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ==================== UPDATE User MODEL ====================
# Add these columns to User model if not already present:
# custom_permissions = Column(Text, nullable=True)  # JSON of granted/denied permissions
# is_suspended = Column(Boolean, default=False)  # Admin can suspend users
# is_frozen = Column(Boolean, default=False)  # Admin can freeze accounts


class FedNowTransaction(Base):
    """Federal Reserve FedNow transaction"""
    __tablename__ = "fednow_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    routing_number = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


# ===== FRAUD DETECTION MODELS =====

class FraudScore(Base):
    """Fraud risk score for transaction"""
    __tablename__ = "fraud_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    score = Column(Numeric(5, 4), default=0.0, nullable=False)  # Numeric for score precision (0.0000 to 1.0000)
    risk_level = Column(String, nullable=False)  # low, medium, high, critical
    decision = Column(String, nullable=True)  # approve, challenge, block
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


class FraudRule(Base):
    """Fraud detection rule"""
    __tablename__ = "fraud_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, nullable=False, unique=True, index=True)
    rule_type = Column(String, nullable=False)  # velocity, amount, location, pattern
    description = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BlockedTransaction(Base):
    """Blocked transaction record"""
    __tablename__ = "blocked_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    fraud_score_id = Column(Integer, ForeignKey("fraud_scores.id"), nullable=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")
    fraud_score = relationship("FraudScore")


class DeviceFingerprint(Base):
    """Device fingerprint for fraud detection"""
    __tablename__ = "device_fingerprints"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class TransactionMonitoring(Base):
    """Transaction monitoring record"""
    __tablename__ = "transaction_monitoring"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    transaction = relationship("Transaction")


class SanctionsCheck(Base):
    """Sanctions screening check"""
    __tablename__ = "sanctions_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    screening_date = Column(DateTime(timezone=True), server_default=func.now())
    match_found = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


# ===== ACCOUNT TYPE MODEL =====

class AccountType(Base):
    """Account type reference"""
    __tablename__ = "account_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)  # checking, savings, business, investment, etc.
    description = Column(String, nullable=True)
    features = Column(String, nullable=True)  # JSON array of features
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===== TOKEN BLACKLIST MODEL =====

class TokenBlacklist(Base):
    """
    Stores invalidated JWT tokens to prevent replay attacks after logout.
    When a user logs out, their token is added to this blacklist.
    Token validation checks if token is in blacklist before allowing access.
    """
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, nullable=False, unique=True, index=True)  # The invalidated JWT token
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # User who logged out
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When token was blacklisted
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Token expiration time from JWT
    
    user = relationship("User")


# ===== ADMIN AUDIT LOG MODEL =====

class AdminAuditLog(Base):
    """
    Audit log for all admin configuration changes.
    Records every change to system settings for compliance.
    """
    __tablename__ = "admin_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)  # e.g., "update_setting", "rotate_api_keys", "toggle_maintenance_mode"
    setting_name = Column(String, nullable=True)  # Name of setting changed
    old_value = Column(String, nullable=True)  # Previous value
    new_value = Column(String, nullable=True)  # New value
    ip_address = Column(String, nullable=True)  # Admin's IP address
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    admin = relationship("User")


# ===== BILL PAY MODELS =====

class Biller(Base):
    __tablename__ = "billers"
    
    id = Column(Integer, primary_key=True, index=True)
    biller_name = Column(String, nullable=False)
    biller_type = Column(String, nullable=False)
    processing_time_days = Column(Integer, default=1)
    active = Column(Boolean, default=True)


class Payee(Base):
    __tablename__ = "payees"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    payee_name = Column(String, nullable=False)
    payee_type = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    routing_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    status = Column(String, default="active")
    last_payment_date = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BillPayment(Base):
    __tablename__ = "bill_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")
    memo = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)
    frequency = Column(String, nullable=True)
    end_date = Column(DateTime, nullable=True)


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("bill_payments.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    receipt_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="generated")


class PaymentFailureLog(Base):
    __tablename__ = "payment_failure_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("bill_payments.id"), nullable=False)
    failure_reason = Column(String, nullable=False)
    failure_date = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=1)


class PaymentSchedule(Base):
    __tablename__ = "payment_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False)  # weekly, biweekly, monthly, quarterly, annual
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class CheckImage(Base):
    __tablename__ = "check_images"
    
    id = Column(Integer, primary_key=True, index=True)
    deposit_id = Column(Integer, ForeignKey("mobile_deposits.id"), nullable=False)
    image_side = Column(String, nullable=False)  # "front" or "back"
    image_data = Column(LargeBinary, nullable=False)
    image_hash = Column(String, nullable=False)
    image_size = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)


class CheckOCRData(Base):
    __tablename__ = "check_ocr_data"
    
    id = Column(Integer, primary_key=True, index=True)
    deposit_id = Column(Integer, ForeignKey("mobile_deposits.id"), nullable=False)
    routing_number = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    check_number = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    date_field = Column(DateTime, nullable=True)
    payee = Column(String, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Float, nullable=True)


OCRResult = CheckOCRData