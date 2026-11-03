"""Priority 3 - Database models for scheduled transfers, webhooks, mobile deposits, and compliance."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey, Time, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import json

# Use the SHARED Base so relationships (User, Account, Transaction) resolve
# across the single SQLAlchemy mapper registry.
from database import Base


class ScheduledTransfer(Base):
    """Model for scheduled recurring transfers."""
    
    __tablename__ = 'scheduled_transfers'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    from_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    to_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
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
        Index('ix_scheduled_transfers_status', 'status'),
    )


class ScheduledTransferExecution(Base):
    """Model for tracking execution of scheduled transfers."""
    
    __tablename__ = 'scheduled_transfer_executions'
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_transfer_id = Column(Integer, ForeignKey('scheduled_transfers.id'), nullable=False, index=True)
    execution_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)  # pending, completed, failed
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    scheduled_transfer = relationship("ScheduledTransfer", back_populates="executions")
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    
    __table_args__ = (
        Index('ix_scheduled_transfer_executions_status', 'status'),
    )


# Webhook, WebhookDelivery, MobileDeposit, FlaggedTransaction are defined in models.py.
# Import them here so services_priority_3.py can reference them from one place.
from models import Webhook, WebhookDelivery, MobileDeposit, FlaggedTransaction  # noqa: F401



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
    
    # country_code index already created by Column(..., index=True)


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
    
    # name and screening_date indices already created by Column(..., index=True)
