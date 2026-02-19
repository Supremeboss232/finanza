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
