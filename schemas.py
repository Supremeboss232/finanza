# schemas.py
# Pydantic models for request/response validation and serialization.

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool
    user_id: int
    email: str
    full_name: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    is_admin: bool
    kyc_status: str = "not_started"  # not_started, pending, approved, rejected
    created_at: datetime
    updated_at: Optional[datetime] = None
    balance: float = 0.0  # User's balance from ledger (admin calculations)
    address: Optional[str] = None  # User address for admin display
    region: Optional[str] = None  # User region/state for admin display
    routing_number: Optional[str] = None  # Routing number for admin display

    class Config:
        from_attributes = True

class AccountBase(BaseModel):
    account_number: str
    balance: float
    currency: str

class AccountCreate(AccountBase):
    pass

class Account(AccountBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    amount: float
    transaction_type: str
    status: str
    description: Optional[str] = None
    reference_number: Optional[str] = None

class TransactionCreate(TransactionBase):
    user_id: int  # REQUIRED: Every transaction must have a user owner
    account_id: int  # REQUIRED: Every transaction must link to an account
    pass

class Transaction(TransactionBase):
    id: int
    user_id: int
    account_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # Allow populating from attributes even if some are missing
        validate_default = False
class KYCInfoBase(BaseModel):
    document_type: str
    document_number: str
    status: str

class KYCInfoCreate(KYCInfoBase):
    pass

class KYCInfo(KYCInfoBase):
    id: int
    user_id: int
    submitted_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FormSubmissionBase(BaseModel):
    form_type: str
    data: str # Can be a dict if you use a JSON type in the DB

class FormSubmissionCreate(FormSubmissionBase):
    pass

class FormSubmission(FormSubmissionBase):
    id: int
    user_id: Optional[int] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


class KYCSubmissionBase(BaseModel):
    document_type: str
    document_file_path: str
    status: str = "pending"


class KYCSubmissionCreate(KYCSubmissionBase):
    pass


class KYCSubmission(KYCSubmissionBase):
    id: int
    user_id: int
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for Deposits
class DepositBase(BaseModel):
    amount: float
    current_balance: Optional[float] = None
    currency: str = "USD"
    interest_rate: float = 0.0
    term_months: int = 12
    maturity_date: Optional[datetime] = None
    status: str = "active"

class DepositCreate(DepositBase):
    pass

class Deposit(DepositBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Loans
class LoanBase(BaseModel):
    amount: float
    interest_rate: float
    term_months: int
    loan_type: Optional[str] = None  # personal, auto, home, student, business
    monthly_payment: float = 0.0
    remaining_balance: float = 0.0
    paid_amount: float = 0.0
    status: str = "pending"
    purpose: Optional[str] = None
    approved_at: Optional[datetime] = None

class LoanCreate(LoanBase):
    pass

class LoanApplicationRequest(BaseModel):
    """Schema for loan application requests from frontend"""
    amount: float
    term_months: int
    loan_type: Optional[str] = None
    purpose: Optional[str] = None
    collateral: Optional[str] = None

class Loan(LoanBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Investments
class InvestmentBase(BaseModel):
    investment_type: str
    amount: float
    current_value: Optional[float] = None
    interest_earned: float = 0.0
    annual_return_rate: float = 0.0
    status: str = "active"
    purpose: Optional[str] = None
    maturity_date: Optional[datetime] = None

class InvestmentCreate(InvestmentBase):
    pass

class Investment(InvestmentBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Cards
class CardBase(BaseModel):
    card_number: str
    card_type: str
    card_holder_name: Optional[str] = None
    expiry_date: str
    balance: float = 0.0
    credit_limit: float = 5000.0
    transaction_limit: float = 10000.0
    status: str = "active"

class CardCreate(CardBase):
    pass

class Card(CardBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Policies
class PolicyBase(BaseModel):
    policy_number: str
    policy_type: str
    coverage_amount: float
    premium: float
    start_date: datetime
    renewal_date: datetime
    status: str = "active"

class PolicyCreate(PolicyBase):
    pass

class Policy(PolicyBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Claims
class ClaimBase(BaseModel):
    claim_number: str
    amount: float
    status: str = "pending"
    description: str

class ClaimCreate(ClaimBase):
    pass

class Claim(ClaimBase):
    id: int
    policy_id: int
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for Budgets
class BudgetBase(BaseModel):
    category: str
    limit: float
    spent: float = 0.0
    month: str

class BudgetCreate(BudgetBase):
    pass

class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Goals
class GoalBase(BaseModel):
    goal_name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: datetime
    status: str = "active"

class GoalCreate(GoalBase):
    pass

class Goal(GoalBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Notifications
class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schemas for Support Tickets
class SupportTicketBase(BaseModel):
    subject: str
    message: str
    priority: str = "normal"

class SupportTicketCreate(SupportTicketBase):
    pass

class SupportTicket(SupportTicketBase):
    id: int
    ticket_number: str
    user_id: Optional[int] = None
    status: str = "open"
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for User Settings
class UserSettingsBase(BaseModel):
    two_factor_enabled: bool = False
    email_notifications: bool = True
    sms_notifications: bool = False
    phone_number: Optional[str] = None
    address: Optional[str] = None
    preferences: Optional[str] = None

class UserSettingsCreate(UserSettingsBase):
    pass

class UserSettings(UserSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schemas for Projects
class ProjectBase(BaseModel):
    project_name: str
    description: str
    status: str = "planning"
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AdminDashboardMetrics(BaseModel):
    total_users: int
    total_transactions: int
    total_volume: float
    total_deposits: float = 0.0
    pending_kyc: int = 0
    recent_users: Optional[List['User']] = None
    recent_transactions: Optional[List['Transaction']] = None

    class Config:
        from_attributes = True

class FundUserRequest(BaseModel):
    email: str
    amount: float
    currency: str = "USD"
    account_type: Optional[str] = None
    fund_source: str = "admin"
    notes: Optional[str] = None
    description: Optional[str] = None
    reference_number: Optional[str] = None

class FundUserResponse(BaseModel):
    success: bool
    message: str
    transaction_id: int
    user_id: int

class AdjustBalanceRequest(BaseModel):
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    operation_type: str = "credit"

class CreateAccountRequest(BaseModel):
    account_number: Optional[str] = None
    currency: str = "USD"
    account_type: str = "savings"  # savings, checking, business
    initial_balance: float = 0.0

class KYCApprovalRequest(BaseModel):
    notes: Optional[str] = None

class KYCRejectionRequest(BaseModel):
    notes: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """Request model for admin password reset"""
    new_password: str

class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile (includes KYC personal details)"""
    # Personal Information
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None
    is_active: Optional[bool] = None
    
    # KYC Personal Details
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    occupation: Optional[str] = None
    employer: Optional[str] = None

class TransactionCreateRequest(BaseModel):
    """Request model for admin creating transactions"""
    user_email: str
    transaction_type: str
    amount: float
    description: Optional[str] = None
    is_admin: Optional[bool] = None

class AccountStatusToggleRequest(BaseModel):
    """Request model for toggling account status"""
    is_active: Optional[bool] = None

class AdminAccessToggleRequest(BaseModel):
    """Request model for toggling admin access"""
    is_admin: Optional[bool] = None

    """Pydantic schemas for Priority 3 features."""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
import json


# ============================================================================
# SCHEDULED TRANSFER SCHEMAS
# ============================================================================

class ScheduledTransferCreate(BaseModel):
    """Schema for creating a scheduled transfer."""
    from_account_id: int = Field(..., gt=0)
    to_account_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    frequency: str = Field(..., pattern="^(once|daily|weekly|monthly|yearly)$")
    start_date: datetime
    end_date: Optional[datetime] = None
    start_time: time
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "from_account_id": 1,
                "to_account_id": 2,
                "amount": 500.00,
                "frequency": "monthly",
                "start_date": "2024-01-15T00:00:00Z",
                "end_date": "2024-12-31T00:00:00Z",
                "start_time": "09:00",
                "description": "Monthly rent payment"
            }
        }


class ScheduledTransferUpdate(BaseModel):
    """Schema for updating a scheduled transfer."""
    amount: Optional[Decimal] = Field(None, gt=0)
    end_date: Optional[datetime] = None
    start_time: Optional[time] = None
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 600.00,
                "description": "Updated rent payment"
            }
        }


class ScheduledTransferResponse(BaseModel):
    """Schema for scheduled transfer response."""
    id: int
    user_id: int
    from_account_id: int
    to_account_id: int
    amount: Decimal
    frequency: str
    start_date: datetime
    end_date: Optional[datetime]
    start_time: time
    status: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ScheduledTransferExecutionResponse(BaseModel):
    """Schema for scheduled transfer execution."""
    id: int
    scheduled_transfer_id: int
    execution_date: datetime
    status: str
    transaction_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# WEBHOOK SCHEMAS
# ============================================================================

class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    events: List[str]
    active: bool = True
    retry_count: int = Field(3, ge=1, le=10)
    timeout_seconds: int = Field(30, ge=5, le=300)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Payment Webhook",
                "url": "https://example.com/webhooks/payment",
                "events": ["transaction.completed", "transfer.failed"],
                "active": True,
                "retry_count": 3,
                "timeout_seconds": 30
            }
        }


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: int
    user_id: int
    name: str
    url: str
    active: bool
    events: List[str]
    retry_count: int
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(self.events, str):
            self.events = json.loads(self.events)
    
    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery."""
    id: int
    webhook_id: int
    event_type: str
    status: str
    http_status: Optional[int]
    attempt_count: int
    error_message: Optional[str]
    last_attempt: Optional[datetime]
    next_retry: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# MOBILE DEPOSIT SCHEMAS
# ============================================================================

class MobileDepositCreate(BaseModel):
    """Schema for creating a mobile deposit."""
    account_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "account_id": 1,
                "amount": 250.00,
                "front_image_url": "https://cdn.example.com/deposits/front_123.jpg",
                "back_image_url": "https://cdn.example.com/deposits/back_123.jpg"
            }
        }


class MobileDepositUpdate(BaseModel):
    """Schema for updating mobile deposit status."""
    status: str = Field(..., pattern="^(pending|approved|rejected|processing)$")
    review_notes: Optional[str] = None
    quality_score: Optional[Decimal] = None


class MobileDepositResponse(BaseModel):
    """Schema for mobile deposit response."""
    id: int
    user_id: int
    account_id: int
    amount: Decimal
    front_image_url: Optional[str]
    back_image_url: Optional[str]
    status: str
    quality_score: Optional[Decimal]
    check_detected: Optional[bool]
    endorsement_found: Optional[bool]
    image_quality_score: Optional[Decimal]
    review_notes: Optional[str]
    reviewed_by: Optional[int]
    created_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# FLAGGED TRANSACTION SCHEMAS
# ============================================================================

class FlaggedTransactionResponse(BaseModel):
    """Schema for flagged transaction."""
    id: int
    transaction_id: int
    user_id: int
    flag_reason: str
    risk_score: Optional[Decimal]
    status: str
    investigation_notes: Optional[str]
    resolution_date: Optional[datetime]
    resolved_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FlaggedTransactionUpdate(BaseModel):
    """Schema for updating flagged transaction."""
    status: Optional[str] = Field(None, pattern="^(flagged|investigating|resolved|approved)$")
    investigation_notes: Optional[str] = None
    risk_score: Optional[Decimal] = None


# ============================================================================
# COUNTRY RISK ASSESSMENT SCHEMAS
# ============================================================================

class CountryRiskAssessmentResponse(BaseModel):
    """Schema for country risk assessment."""
    id: int
    country_code: str
    country_name: str
    risk_rating: str
    aml_risk: Optional[str]
    cft_risk: Optional[str]
    transaction_limit: Optional[Decimal]
    last_updated: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# SANCTIONS SCREENING SCHEMAS
# ============================================================================

class SanctionsScreeningResponse(BaseModel):
    """Schema for sanctions screening."""
    id: int
    name: str
    screening_date: datetime
    database: str
    match_found: bool
    confidence_score: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SanctionsScreeningRequest(BaseModel):
    """Schema for sanctions screening request."""
    name: str
    database: Optional[str] = "OFAC"
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Smith",
                "database": "OFAC"
            }
        }


# ============================================================================
# COMPLIANCE REPORT SCHEMAS
# ============================================================================

class ComplianceReportResponse(BaseModel):
    """Schema for compliance report."""
    total_flagged_transactions: int
    pending_investigations: int
    resolved_cases: int
    high_risk_users: int
    sanctions_matches: int
    aml_alerts: int
    period_start: datetime
    period_end: datetime
    
    class Config:
        from_attributes = True


class AdminWebhooksStatsResponse(BaseModel):
    """Schema for admin webhooks statistics."""
    total_webhooks: int
    active_webhooks: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    pending_deliveries: int
    average_response_time_ms: float
    last_7_days_success_rate: float
    
    class Config:
        from_attributes = True
