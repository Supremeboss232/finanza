"""Priority 3 - Base database schema for all new features.

Revision ID: 001_priority_3_base
Revises: None
Create Date: 2024-01-29

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001_priority_3_base'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all Priority 3 tables."""
    
    # Scheduled Transfers Table
    op.create_table(
        'scheduled_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('from_account_id', sa.Integer(), nullable=False),
        sa.Column('to_account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('frequency', sa.String(50), nullable=False),  # once, daily, weekly, monthly, yearly
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='active'),  # active, paused, cancelled, completed
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.Index('ix_scheduled_transfers_user_id', 'user_id'),
        sa.Index('ix_scheduled_transfers_status', 'status'),
    )
    
    # Scheduled Transfer Executions Table
    op.create_table(
        'scheduled_transfer_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_transfer_id', sa.Integer(), nullable=False),
        sa.Column('execution_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),  # pending, completed, failed
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['scheduled_transfer_id'], ['scheduled_transfers.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ondelete='SET NULL'),
        sa.Index('ix_scheduled_transfer_executions_scheduled_transfer_id', 'scheduled_transfer_id'),
        sa.Index('ix_scheduled_transfer_executions_status', 'status'),
    )
    
    # Webhooks Table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('secret_key', sa.String(255), nullable=True),
        sa.Column('events', sa.Text(), nullable=False),  # JSON array
        sa.Column('retry_count', sa.Integer(), nullable=False, default=3),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=30),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.Index('ix_webhooks_user_id', 'user_id'),
        sa.Index('ix_webhooks_active', 'active'),
    )
    
    # Webhook Deliveries Table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),  # JSON
        sa.Column('status', sa.String(50), nullable=False),  # pending, success, failed
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('next_retry', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.Index('ix_webhook_deliveries_webhook_id', 'webhook_id'),
        sa.Index('ix_webhook_deliveries_status', 'status'),
        sa.Index('ix_webhook_deliveries_created_at', 'created_at'),
    )
    
    # Mobile Deposits Table
    op.create_table(
        'mobile_deposits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('front_image_url', sa.String(2048), nullable=True),
        sa.Column('back_image_url', sa.String(2048), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),  # pending, approved, rejected, processing
        sa.Column('quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('check_detected', sa.Boolean(), nullable=True),
        sa.Column('endorsement_found', sa.Boolean(), nullable=True),
        sa.Column('image_quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['user.id'], ondelete='SET NULL'),
        sa.Index('ix_mobile_deposits_user_id', 'user_id'),
        sa.Index('ix_mobile_deposits_status', 'status'),
        sa.Index('ix_mobile_deposits_created_at', 'created_at'),
    )
    
    # Flagged Transactions Table
    op.create_table(
        'flagged_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('flag_reason', sa.String(255), nullable=False),
        sa.Column('risk_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),  # flagged, investigating, resolved, approved
        sa.Column('investigation_notes', sa.Text(), nullable=True),
        sa.Column('resolution_date', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['user.id'], ondelete='SET NULL'),
        sa.Index('ix_flagged_transactions_user_id', 'user_id'),
        sa.Index('ix_flagged_transactions_status', 'status'),
    )
    
    # Country Risk Assessment Table
    op.create_table(
        'country_risk_assessment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country_code', sa.String(2), nullable=False, unique=True),
        sa.Column('country_name', sa.String(255), nullable=False),
        sa.Column('risk_rating', sa.String(50), nullable=False),  # High, Medium, Low
        sa.Column('aml_risk', sa.String(50), nullable=True),
        sa.Column('cft_risk', sa.String(50), nullable=True),
        sa.Column('transaction_limit', sa.Numeric(15, 2), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_country_risk_country_code', 'country_code'),
    )
    
    # Sanctions Screening Table
    op.create_table(
        'sanctions_screening',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('screening_date', sa.DateTime(), nullable=False),
        sa.Column('database', sa.String(50), nullable=False),  # OFAC, UN, EU, UK
        sa.Column('match_found', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_sanctions_screening_name', 'name'),
        sa.Index('ix_sanctions_screening_screening_date', 'screening_date'),
    )


def downgrade():
    """Drop all Priority 3 tables."""
    op.drop_table('sanctions_screening')
    op.drop_table('country_risk_assessment')
    op.drop_table('flagged_transactions')
    op.drop_table('mobile_deposits')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
    op.drop_table('scheduled_transfer_executions')
    op.drop_table('scheduled_transfers')
