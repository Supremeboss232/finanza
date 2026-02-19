"""Priority 3 - Database models for scheduled transfers, webhooks, mobile deposits, and compliance."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey, Time, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class ScheduledTransfer(Base):
    """Model for scheduled recurring transfers."""
    
    __tablename__ = 'scheduled_transfers'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    from_account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    to_account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    frequency = Column(String(50), nullable=False)  # once, daily, weekly, monthly, yearly
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    start_time = Column(Time, nullable=False)
    status = Column(String(50), nullable=False, default='active')  # active, paused, cancelled, completed
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="scheduled_transfers")
    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    executions = relationship("ScheduledTransferExecution", back_populates="scheduled_transfer", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_scheduled_transfers_user_id', 'user_id'),
        Index('ix_scheduled_transfers_status', 'status'),
    )


class ScheduledTransferExecution(Base):
    """Model for tracking execution of scheduled transfers."""
    
    __tablename__ = 'scheduled_transfer_executions'
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_transfer_id = Column(Integer, ForeignKey('scheduled_transfers.id'), nullable=False, index=True)
    execution_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)  # pending, completed, failed
    transaction_id = Column(Integer, ForeignKey('transaction.id'), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    scheduled_transfer = relationship("ScheduledTransfer", back_populates="executions")
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    
    __table_args__ = (
        Index('ix_scheduled_transfer_executions_scheduled_transfer_id', 'scheduled_transfer_id'),
        Index('ix_scheduled_transfer_executions_status', 'status'),
    )


class Webhook(Base):
    """Model for user webhooks."""
    
    __tablename__ = 'webhooks'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    secret_key = Column(String(255), nullable=True)
    events = Column(Text, nullable=False)  # JSON array of event types
    retry_count = Column(Integer, default=3, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")
    
    def get_events(self) -> list:
        """Parse JSON events field."""
        try:
            return json.loads(self.events)
        except:
            return []
    
    def set_events(self, events: list):
        """Set events as JSON string."""
        self.events = json.dumps(events)
    
    __table_args__ = (
        Index('ix_webhooks_user_id', 'user_id'),
        Index('ix_webhooks_active', 'active'),
    )


class WebhookDelivery(Base):
    """Model for tracking webhook deliveries."""
    
    __tablename__ = 'webhook_deliveries'
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey('webhooks.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)  # JSON payload
    status = Column(String(50), nullable=False, index=True)  # pending, success, failed
    http_status = Column(Integer, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime, nullable=True)
    next_retry = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")
    
    def get_payload(self) -> dict:
        """Parse JSON payload."""
        try:
            return json.loads(self.payload)
        except:
            return {}
    
    def set_payload(self, payload: dict):
        """Set payload as JSON string."""
        self.payload = json.dumps(payload)
    
    __table_args__ = (
        Index('ix_webhook_deliveries_webhook_id', 'webhook_id'),
        Index('ix_webhook_deliveries_status', 'status'),
        Index('ix_webhook_deliveries_created_at', 'created_at'),
    )


class MobileDeposit(Base):
    """Model for mobile check deposits."""
    
    __tablename__ = 'mobile_deposits'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    front_image_url = Column(String(2048), nullable=True)
    back_image_url = Column(String(2048), nullable=True)
    status = Column(String(50), nullable=False, index=True)  # pending, approved, rejected, processing
    quality_score = Column(Numeric(5, 2), nullable=True)
    check_detected = Column(Boolean, nullable=True)
    endorsement_found = Column(Boolean, nullable=True)
    image_quality_score = Column(Numeric(5, 2), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="mobile_deposits")
    account = relationship("Account", foreign_keys=[account_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    __table_args__ = (
        Index('ix_mobile_deposits_user_id', 'user_id'),
        Index('ix_mobile_deposits_status', 'status'),
        Index('ix_mobile_deposits_created_at', 'created_at'),
    )


class FlaggedTransaction(Base):
    """Model for flagged compliance transactions."""
    
    __tablename__ = 'flagged_transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey('transaction.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    flag_reason = Column(String(255), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), nullable=False, index=True)  # flagged, investigating, resolved, approved
    investigation_notes = Column(Text, nullable=True)
    resolution_date = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    user = relationship("User", foreign_keys=[user_id], back_populates="flagged_transactions")
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    __table_args__ = (
        Index('ix_flagged_transactions_user_id', 'user_id'),
        Index('ix_flagged_transactions_status', 'status'),
    )


class CountryRiskAssessment(Base):
    """Model for country-level risk assessment."""
    
    __tablename__ = 'country_risk_assessment'
    
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(2), nullable=False, unique=True, index=True)
    country_name = Column(String(255), nullable=False)
    risk_rating = Column(String(50), nullable=False)  # High, Medium, Low
    aml_risk = Column(String(50), nullable=True)
    cft_risk = Column(String(50), nullable=True)
    transaction_limit = Column(Numeric(15, 2), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('ix_country_risk_country_code', 'country_code'),
    )


class SanctionsScreening(Base):
    """Model for sanctions list screening records."""
    
    __tablename__ = 'sanctions_screening'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    screening_date = Column(DateTime, nullable=False, index=True)
    database = Column(String(50), nullable=False)  # OFAC, UN, EU, UK
    match_found = Column(Boolean, nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('ix_sanctions_screening_name', 'name'),
        Index('ix_sanctions_screening_screening_date', 'screening_date'),
    )
