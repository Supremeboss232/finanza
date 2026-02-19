# models.py
# SQLAlchemy models defining database tables (User, Admin, Transactions, KYC, etc.).

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base # Assuming database.py defines Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    account_number = Column(String, unique=True, index=True, nullable=True)
    account_type = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    kyc_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (examples)
    accounts = relationship("Account", back_populates="owner")
    transactions = relationship("Transaction", back_populates="user")
    kyc_info = relationship("KYCInfo", uselist=False, back_populates="user")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Float)
    transaction_type = Column(String) # e.g., "deposit", "withdrawal", "transfer"
    status = Column(String, default="pending") # e.g., "pending", "completed", "failed"
    description = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")

class KYCInfo(Base):
    __tablename__ = "kyc_info"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    document_type = Column(String) # e.g., "passport", "driver_license"
    document_number = Column(String)
    status = Column(String, default="pending") # e.g., "pending", "approved", "rejected"
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="kyc_info")

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
    amount = Column(Float)  # Initial deposit amount
    currency = Column(String, default="USD")
    interest_rate = Column(Float, default=0.0)  # Annual interest rate
    maturity_date = Column(DateTime(timezone=True), nullable=True)  # When deposit matures
    balance = Column(Float)  # Current balance with interest
    status = Column(String, default="active")  # active, matured, withdrawn
    withdrawal_amount = Column(Float, default=0.0)  # Amount withdrawn via ATM/Agent
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User")

class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)  # Original loan amount
    interest_rate = Column(Float)  # Annual interest rate
    term_months = Column(Integer)  # Loan term
    monthly_payment = Column(Float, default=0.0)  # Monthly payment amount
    remaining_balance = Column(Float)  # Current balance owed
    paid_amount = Column(Float, default=0.0)  # Amount already paid
    status = Column(String, default="pending")  # pending, approved, active, completed, defaulted
    purpose = Column(String, nullable=True)  # Loan purpose
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User")

class Investment(Base):
    __tablename__ = "investments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    investment_type = Column(String)  # Stock, Bond, Mutual Fund, Insurance, etc.
    amount = Column(Float)  # Initial investment amount
    current_value = Column(Float)  # Current portfolio value
    interest_earned = Column(Float, default=0.0)  # Total interest/returns earned
    annual_return_rate = Column(Float, default=0.0)  # Expected annual return %
    status = Column(String, default="active")  # active, pending, matured, liquidated
    purpose = Column(String, nullable=True)  # Insurance, Retirement, Education, etc.
    maturity_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User")

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    card_number = Column(String, unique=True)
    card_type = Column(String)  # Debit, Credit, Savings
    expiry_date = Column(String)
    balance = Column(Float, default=0.0)  # Card balance
    credit_limit = Column(Float, default=5000.0)  # Credit limit if credit card
    transaction_limit = Column(Float, default=10000.0)  # Daily/transaction limit
    status = Column(String, default="active")  # active, blocked, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User")


# NEW BANKING FEATURE MODELS

class Transfer(Base):
    """Money transfer records."""
    __tablename__ = "transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    from_account_id = Column(Integer, ForeignKey("accounts.id"))
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True)
    transfer_type = Column(String)  # e.g., "domestic", "international", "bill_pay"
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # e.g., "pending", "confirmed", "completed", "failed", "cancelled"
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    memo = Column(String, nullable=True)
    reference_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")
    from_account = relationship("Account")
    recipient = relationship("Recipient", back_populates="transfers")


class Recipient(Base):
    """Saved transfer recipients/payees."""
    __tablename__ = "recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    account_type = Column(String)  # e.g., "checking", "savings", "money_market"
    account_number = Column(String)
    account_number_masked = Column(String)  # e.g., "****1234"
    routing_number = Column(String)
    bank_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    transfer_count = Column(Integer, default=0)
    last_transfer_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")
    transfers = relationship("Transfer", back_populates="recipient")


class LoginHistory(Base):
    """Record of user login attempts."""
    __tablename__ = "login_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String)
    device_info = Column(String)  # e.g., "Chrome on Windows"
    location = Column(String, nullable=True)
    status = Column(String, default="success")  # e.g., "success", "failed"
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    logout_time = Column(DateTime(timezone=True), nullable=True)
    session_id = Column(String, unique=True, nullable=True)
    
    user = relationship("User")


class TrustedDevice(Base):
    """User's trusted/recognized devices."""
    __tablename__ = "trusted_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_name = Column(String)  # e.g., "My Laptop", "iPhone"
    device_type = Column(String)  # e.g., "Windows PC", "iOS", "Android"
    device_id = Column(String, unique=True, index=True)
    ip_address = Column(String)
    user_agent = Column(String, nullable=True)
    is_current = Column(Boolean, default=False)
    is_trusted = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class TwoFactorAuth(Base):
    """Two-factor authentication settings."""
    __tablename__ = "two_factor_auth"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    is_enabled = Column(Boolean, default=False)
    method = Column(String)  # e.g., "authenticator", "sms", "email"
    secret_key = Column(String, nullable=True)  # For authenticator app
    backup_codes = Column(String, nullable=True)  # JSON list of backup codes
    phone_number = Column(String, nullable=True)  # For SMS 2FA
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    enabled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")


class AlertPreference(Base):
    """User's alert and notification preferences."""
    __tablename__ = "alert_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Channels
    enable_in_app = Column(Boolean, default=True)
    enable_email = Column(Boolean, default=True)
    enable_sms = Column(Boolean, default=False)
    enable_push = Column(Boolean, default=False)
    
    # Alert types
    transaction_alerts = Column(Boolean, default=True)
    security_alerts = Column(Boolean, default=True)
    account_alerts = Column(Boolean, default=True)
    marketing_alerts = Column(Boolean, default=False)
    
    # Thresholds
    large_transaction_threshold = Column(Float, default=5000.0)
    low_balance_threshold = Column(Float, default=100.0)
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String, default="22:00")  # HH:MM format
    quiet_hours_end = Column(String, default="08:00")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")


class Alert(Base):
    """User notifications/alerts."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    alert_type = Column(String)  # e.g., "transaction", "security", "account", "marketing"
    subtype = Column(String, nullable=True)  # e.g., "large_transfer", "login", "low_balance"
    title = Column(String)
    message = Column(String)
    is_read = Column(Boolean, default=False)
    priority = Column(String, default="medium")  # e.g., "low", "medium", "high"
    action_url = Column(String, nullable=True)  # Link to related content
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")